'use strict';

const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
const terminal = new Set([
  'failed', 'deployment_failed', 'deployment_content_failed', 'deployment_cancelled', 'deployment_lost'
]);

module.exports = async ({github, context, core, artifactId, pause = wait}) => {
  artifactId = Number(artifactId);
  if (!Number.isSafeInteger(artifactId) || artifactId <= 0) throw new Error('Pages upload did not return an artifact ID');
  const repo = context.repo;
  // The upload output identifies this run's artifact without relying on the
  // same-run artifact name listing, which has returned an empty result.
  let available = false;
  for (let attempt = 0; attempt < 12; attempt++) {
    try {
      const {data} = await github.rest.actions.getArtifact({...repo, artifact_id: artifactId});
      if (data.name !== 'github-pages' || data.expired) throw new Error('Pages artifact is invalid or expired');
      available = true;
      break;
    } catch (error) {
      if (error.status !== 404 && !(error.status >= 500)) throw error;
      await pause(5000);
    }
  }
  if (!available) throw new Error('GitHub did not register the uploaded Pages artifact in time');

  let release;
  try {
    ({data: release} = await github.request('POST /repos/{owner}/{repo}/pages/deployments', {
      ...repo, artifact_id: artifactId, pages_build_version: context.sha, oidc_token: await core.getIDToken()
    }));
  } catch (error) {
    throw new Error(`GitHub rejected the Pages deployment request (HTTP ${error.status ?? 'unknown'})`);
  }
  const deployment = release.id ?? release.status_url?.split('/').at(-1);
  if (!deployment || !release.page_url) throw new Error('GitHub returned an incomplete Pages deployment');
  for (let attempt = 0; attempt < 60; attempt++) {
    await pause(5000);
    let status;
    try {
      const {data} = await github.request('GET /repos/{owner}/{repo}/pages/deployments/{deployment}', {
        ...repo, deployment
      });
      status = data.status;
    } catch (error) {
      if (error.status === 404 || error.status >= 500) continue;
      throw error;
    }
    if (status === 'succeed') {
      core.setOutput('page_url', release.page_url);
      core.info(`Published ${release.page_url}`);
      return;
    }
    if (terminal.has(status)) throw new Error(`GitHub Pages deployment ended with status ${status}`);
  }
  throw new Error('GitHub Pages did not confirm deployment within five minutes');
};
