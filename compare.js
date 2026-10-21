(() => {
  'use strict';
  const data = JSON.parse(document.getElementById('comparison-data').textContent);
  const rows = data.rows;
  const frozenAssessments = new Map(rows.map(r=>[r.ticker,r.model?.assessment]));
  function refreshAssessments(){
    for(const r of rows){
      const current=InvestorAceAssessment.project(frozenAssessments.get(r.ticker),{objections:r.model?.objections});
      Object.assign(r.model,{assessment:current,score:current.model_score,rating:current.rating,
        review_required:!current.quality_rank_eligible,quality_rank_eligible:current.quality_rank_eligible});
    }
  }
  const byTicker = new Map(rows.map(r => [r.ticker, r]));
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const finite = value => typeof value === 'number' && Number.isFinite(value);
  const params = new URLSearchParams(location.search);
  const translations = {
    scoreboard:['Scoreboard','Scoreboard','Panel de puntuaciones'], scanner:['Stock scanner','Aktien-Scanner','Escáner de acciones'],
    compare:['Compare stocks','Aktien vergleichen','Comparar acciones'], language:['Language','Sprache','Idioma'],
    eyebrow:['UNIVERSE / FUNDAMENTALS','UNIVERSUM / FUNDAMENTALDATEN','UNIVERSO / FUNDAMENTALES'],
    intro:['Look beneath the ticker. Compare earnings, cash generation, debt and share supply.','Vergleiche Gewinne, Cashflow, Schulden und Aktienanzahl deiner Unternehmen.','Compara beneficios, generación de caja, deuda y número de acciones.'],
    trackedStocks:['universe stocks','Aktien im Universum','acciones del universo'],
    firstStock:['First stock','Erste Aktie','Primera acción'], secondStock:['Second stock','Zweite Aktie','Segunda acción'],
    period:['Statement period','Berichtszeitraum','Periodo contable'], annualOnly:['Annual statements · up to 4 fiscal years','Jahresabschlüsse · bis zu 4 Geschäftsjahre','Estados anuales · hasta 4 ejercicios'],
    share:['Copy link','Link kopieren','Copiar enlace'], copied:['Link copied','Link kopiert','Enlace copiado'], export:['Export CSV ↓','CSV exportieren ↓','Exportar CSV ↓'],
    financials:['Financial comparison','Finanzvergleich','Comparación financiera'],
    units:['Amounts and shares in millions; currencies stay separate. Ratios use % or ×.','Beträge und Aktien in Millionen; Währungen bleiben getrennt. Kennzahlen in % oder ×.','Importes y acciones en millones; cada moneda se conserva. Ratios en % o ×.'],
    noRanking:['Descriptive comparison','Beschreibender Vergleich','Comparación descriptiva'],
    all:['All metrics','Alle Kennzahlen','Todas las métricas'], income:['Income','Ergebnis','Resultados'], cashFlow:['Cash flow','Cashflow','Flujo de caja'], balanceSheet:['Balance sheet','Bilanz','Balance'], shareSupply:['Share supply','Aktienanzahl','Acciones'],
    marketNote:['Outstanding shares and free float are provider snapshots at retrieval, not fiscal-year averages. Their source observation dates are not supplied.','Ausstehende Aktien und Streubesitz sind Anbieter-Snapshots beim Abruf, keine Jahresdurchschnitte. Die ursprünglichen Beobachtungsdaten fehlen.','Las acciones en circulación y el capital flotante son datos del proveedor al descargarlos, no promedios anuales. El proveedor no indica sus fechas originales.'],
    methodTitle:['Definitions, limitations & sources','Definitionen, Grenzen & Quellen','Definiciones, limitaciones y fuentes'], definitions:['Definitions','Definitionen','Definiciones'], limits:['Interpretation','Einordnung','Interpretación'],
    methodCash:['Free cash flow = operating cash flow − absolute capital expenditure, using the same fiscal year. Net debt = total debt − cash and short-term investments (cash equivalents if investments are unavailable). Debt and lease coverage follow the provider.','Free Cashflow = operativer Cashflow − absoluter Investitionsbetrag desselben Geschäftsjahres. Nettoschulden = Gesamtschulden − liquide Mittel und kurzfristige Anlagen (nur Zahlungsmitteläquivalente, falls Anlagen fehlen). Schulden und Leasing folgen der Anbieterdefinition.','Flujo libre = flujo operativo − inversión de capital en valor absoluto, del mismo ejercicio. Deuda neta = deuda total − efectivo e inversiones a corto plazo (solo equivalentes si faltan inversiones). La inclusión de arrendamientos depende del proveedor.'],
    methodDilution:['Dilution = year-over-year change in diluted weighted-average shares. A negative value means net contraction of that average, not proof of gross buybacks. Splits, acquisitions and ADR or share-class differences need review. Stock compensation is shown separately.','Verwässerung = jährliche Veränderung der verwässerten gewichteten Durchschnittsaktienzahl. Negative Werte zeigen eine Nettoabnahme dieses Durchschnitts, keinen Nachweis der Bruttorückkäufe. Splits, Übernahmen, ADRs und Aktienklassen sind gesondert zu prüfen. Aktienvergütung wird separat gezeigt.','Dilución = cambio interanual del promedio ponderado de acciones diluidas. Un valor negativo indica contracción neta de ese promedio, no demuestra recompras brutas. Splits, adquisiciones, ADR y clases de acciones requieren revisión. La remuneración en acciones figura por separado.'],
    methodLimits:['Yahoo Finance aggregates reported data; these figures have not received a complete primary-source review. Fiscal years can end on different dates. Historical data may be restated. This page does not convert currencies or estimate missing values.','Yahoo Finance aggregiert veröffentlichte Daten; eine vollständige Primärquellenprüfung fehlt. Geschäftsjahre können unterschiedlich enden. Historische Daten können angepasst sein. Währungen werden nicht umgerechnet; fehlende Werte werden nicht geschätzt.','Yahoo Finance agrega datos publicados; estas cifras no cuentan con una revisión completa de fuentes primarias. Los ejercicios pueden terminar en fechas distintas y los históricos pueden revisarse. No se convierten monedas ni se estiman valores ausentes.'],
    methodFramework:['Reported FCF here is separate from InvestorAce sustainable FCF, AFFO, distributable cash flow or mid-cycle assumptions. Regime fit and the fundamental score remain separate. No scores or portfolio weights change.','Der hier ausgewiesene FCF ist von nachhaltigem FCF, AFFO, ausschüttbarem Cashflow und Mid-Cycle-Annahmen in InvestorAce getrennt. Regime-Fit und Fundamentalscore bleiben getrennt. Scores und Portfoliogewichte ändern sich nicht.','El FCF de esta página es independiente del FCF sostenible, AFFO, flujo distribuible y supuestos de mitad de ciclo de InvestorAce. La afinidad de régimen y el score fundamental siguen separados. No cambian los scores ni los pesos de cartera.'],
    footer:['Know what you are comparing.','Wissen, was du vergleichst.','Entiende lo que comparas.'],
    latestFY:['Latest fiscal year','Letztes Geschäftsjahr','Último ejercicio'], priorFY:['1 fiscal year earlier','1 Geschäftsjahr zuvor','1 ejercicio anterior'],
    twoFY:['2 fiscal years earlier','2 Geschäftsjahre zuvor','2 ejercicios anteriores'], threeFY:['3 fiscal years earlier','3 Geschäftsjahre zuvor','3 ejercicios anteriores'],
    revenue:['Revenue','Umsatz','Ingresos'], revenue_growth:['Revenue growth · YoY','Umsatzwachstum · ggü. Vorjahr','Crecimiento de ingresos · interanual'],
    gross_profit:['Gross profit','Bruttogewinn','Beneficio bruto'], gross_margin:['Gross margin','Bruttomarge','Margen bruto'],
    operating_income:['Operating income','Operatives Ergebnis','Beneficio operativo'], operating_margin:['Operating margin','Operative Marge','Margen operativo'], ebitda:['EBITDA','EBITDA','EBITDA'],
    net_income:['Net income','Nettogewinn','Beneficio neto'], net_margin:['Net margin','Nettomarge','Margen neto'],
    ocf:['Operating cash flow','Operativer Cashflow','Flujo de caja operativo'], capex:['Capital expenditure','Investitionen (Capex)','Inversión de capital'],
    fcf:['Free cash flow','Free Cashflow','Flujo de caja libre'], fcf_margin:['FCF margin','FCF-Marge','Margen de FCF'],
    stock_comp:['Stock-based compensation','Aktienbasierte Vergütung','Remuneración en acciones'], buybacks:['Share repurchases','Aktienrückkäufe','Recompras de acciones'],
    cash:['Cash & short-term investments','Liquide Mittel & kurzfristige Anlagen','Efectivo e inversiones a corto plazo'], debt:['Total debt','Gesamtschulden','Deuda total'], net_debt:['Net debt','Nettoschulden','Deuda neta'],
    assets:['Total assets','Bilanzsumme','Activos totales'], liabilities:['Total liabilities','Gesamtverbindlichkeiten','Pasivos totales'], equity:['Shareholders’ equity','Eigenkapital','Patrimonio de accionistas'],
    net_debt_ebitda:['Net debt / EBITDA','Nettoschulden / EBITDA','Deuda neta / EBITDA'], debt_equity:['Debt / equity','Schulden / Eigenkapital','Deuda / patrimonio'],
    shares_outstanding:['Outstanding shares','Ausstehende Aktien','Acciones en circulación'], float_shares:['Free-float shares','Aktien im Streubesitz','Acciones de capital flotante'],
    float_pct:['Free float / outstanding shares','Streubesitz / ausstehende Aktien','Capital flotante / acciones en circulación'], shares_basic:['Basic average shares','Unverwässerte Durchschnittsaktien','Promedio de acciones básicas'],
    shares_diluted:['Diluted average shares','Verwässerte Durchschnittsaktien','Promedio de acciones diluidas'], dilution:['Net dilution · YoY','Nettoverwässerung · ggü. Vorjahr','Dilución neta · interanual'],
    millions:['million','Millionen','millones'], unavailable:['Unavailable','Nicht verfügbar','No disponible'], partial:['Partial data','Teildaten','Datos parciales'], cached:['Previous snapshot','Älterer Snapshot','Datos conservados'], provider:['Provider data','Anbieterdaten','Datos del proveedor'],
    fy:['FY ended','Geschäftsjahresende','Cierre del ejercicio'], retrieved:['Retrieved','Abgerufen','Descargado'],
    snapshot:['Data snapshot','Daten-Snapshot','Datos descargados'],
    notAvailable:['Not available for this fiscal year','Für dieses Geschäftsjahr nicht verfügbar','No disponible para este ejercicio'],
    history:['Revenue history','Umsatzhistorie','Histórico de ingresos'], independentScale:['separate scales','eigene Skalen','escalas separadas'],
    currencyWarning:['Different reporting currencies. Monetary amounts are shown in each issuer’s currency; no direct amount difference is calculated.','Unterschiedliche Berichtswährungen. Geldbeträge bleiben in der jeweiligen Währung; eine direkte Betragsdifferenz wird nicht berechnet.','Monedas contables distintas. Cada importe conserva su moneda; no se calcula una diferencia monetaria directa.'],
    dateWarning:['Different fiscal-year ends. Read the dates above each column; annual periods do not necessarily cover the same months.','Unterschiedliche Geschäftsjahresenden. Beachte die Daten über den Spalten; die Jahre umfassen nicht zwingend dieselben Monate.','Cierres de ejercicio distintos. Revisa las fechas de cada columna; los periodos anuales no necesariamente cubren los mismos meses.'],
    missingWarning:['Some requested data is unavailable. A dash means missing, not zero.','Einige Daten fehlen. Ein Strich bedeutet fehlend, nicht null.','Faltan algunos datos. Un guion indica ausencia, no cero.'],
    universeOnly:['The requested ticker is outside your universe. Choose from the 76 tracked stocks.','Der angefragte Ticker liegt außerhalb des Universums. Wähle eine erfasste Aktie.','El ticker solicitado está fuera del universo. Elige una acción de la lista.'],
    sameStock:['Both selectors contain the same stock. Choose two different stocks to compare.','Beide Felder enthalten dieselbe Aktie. Wähle zwei verschiedene Titel.','Ambos selectores contienen la misma acción. Elige dos acciones distintas.'],
    stale:['This snapshot is over 14 days old. Check the retrieval time before using it.','Dieser Snapshot ist älter als 14 Tage. Prüfe den Abrufzeitpunkt vor der Nutzung.','Estos datos tienen más de 14 días. Revisa la fecha de descarga antes de utilizarlos.'],
    FLOAT_EXCEEDS_SHARES:['Provider float exceeds outstanding shares; the float percentage is withheld.','Anbieter-Streubesitz übersteigt ausstehende Aktien; die Streubesitzquote wird zurückgehalten.','El flotante del proveedor supera las acciones en circulación; no se calcula su porcentaje.'],
    FINANCIAL_CURRENCY_UNKNOWN:['Financial reporting currency is unknown; no quote-currency substitution is used.','Berichtswährung unbekannt; die Kurswährung wird nicht als Ersatz verwendet.','Se desconoce la moneda contable; no se sustituye por la moneda de cotización.'],
    SHARE_ACTION_REVIEW:['Large share-count change: verify corporate actions before interpreting dilution.','Große Aktienzahlveränderung: Kapitalmaßnahmen vor Einordnung der Verwässerung prüfen.','Cambio grande en acciones: verifica las operaciones de capital antes de interpretar la dilución.'],
    NO_STATEMENTS:['Annual statements could not be retrieved.','Jahresabschlüsse konnten nicht abgerufen werden.','No se pudieron obtener los estados anuales.'],
    OLD_FINANCIALS:['The latest fiscal-year end is more than 550 days old.','Das letzte Geschäftsjahresende liegt über 550 Tage zurück.','El último cierre anual tiene más de 550 días.'],
    SECURITY_TYPE_REVIEW:['The provider does not identify this listing as common equity. Verify the security type.','Der Anbieter kennzeichnet diesen Titel nicht als Aktie. Wertpapierart prüfen.','El proveedor no clasifica este símbolo como acción. Verifica el tipo de valor.'],
    REFRESH_FAILED:['The latest refresh failed. The previous snapshot and its original retrieval time are retained.','Der letzte Abruf scheiterte. Vorheriger Snapshot und ursprünglicher Abrufzeitpunkt bleiben erhalten.','La última actualización falló. Se conservan los datos y la fecha de descarga anteriores.'],
    PROVIDER_REQUEST_PARTIAL:['Some provider requests failed; the available fields are shown.','Einige Anbieterabfragen scheiterten; verfügbare Felder werden gezeigt.','Algunas consultas al proveedor fallaron; se muestran los campos disponibles.'],
    annualNote:['Annual · matching fiscal-year end','Jährlich · gleiches Geschäftsjahresende','Anual · mismo cierre de ejercicio'],
    fcfNote:['Operating cash flow − absolute Capex','Operativer Cashflow − absoluter Capex','Flujo operativo − Capex absoluto'],
    debtNote:['Provider definition; lease coverage may differ','Anbieterdefinition; Leasingumfang kann abweichen','Definición del proveedor; arrendamientos pueden variar'],
    cashNote:['Short-term investments included when available','Kurzfristige Anlagen enthalten, soweit verfügbar','Incluye inversiones a corto plazo si se facilitan'],
    averageNote:['Fiscal-year weighted average','Gewichteter Geschäftsjahresdurchschnitt','Promedio ponderado del ejercicio'],
    currentNote:['Provider snapshot · retrieval date below','Anbieter-Snapshot · Abrufdatum unten','Datos del proveedor · fecha de descarga debajo'],
    dilutionNote:['Change in diluted average shares; review splits','Änderung verwässerter Durchschnittsaktien; Splits prüfen','Cambio de promedio diluido; revisar splits'],
    percentage:['Percent','Prozent','Porcentaje'], multiple:['Multiple','Vielfaches','Múltiplo'], metric:['Metric','Kennzahl','Métrica'], source:['Source','Quelle','Fuente'],
    duelEyebrow:['THE FINANCIAL DUEL','DAS FINANZDUELL','EL DUELO FINANCIERO'],
    duelTitle:['Two challengers. Five rounds.','Zwei Kontrahenten. Fünf Runden.','Dos rivales. Cinco asaltos.'],
    duelRuleShort:['1 point per round won','1 Punkt pro gewonnener Runde','1 punto por asalto ganado'],
    duelWinner:['Winner on points: {ticker}','Punktsieger: {ticker}','Ganador por puntos: {ticker}'],
    duelProvisional:['Provisional lead: {ticker}','Vorläufig vorn: {ticker}','Ventaja provisional: {ticker}'],
    duelDraw:['Draw — no winner','Unentschieden — kein Sieger','Empate — sin ganador'],
    duelOpen:['The fight is undecided','Das Duell ist noch offen','El duelo sigue abierto'],
    duelSame:['Choose two different challengers','Wähle zwei verschiedene Kontrahenten','Elige dos rivales distintos'],
    comparableRounds:['comparable rounds','vergleichbare Runden','asaltos comparables'],
    drawnRounds:['drawn','unentschieden','empatados'],
    roundGrowth:['Growth','Wachstum','Crecimiento'], roundProfit:['Profitability','Profitabilität','Rentabilidad'],
    roundCash:['Cash generation','Cash-Generierung','Generación de caja'], roundDebt:['Debt burden','Verschuldung','Endeudamiento'],
    roundDilution:['Share dilution','Verwässerung','Dilución'],
    higherWins:['Higher wins','Höher gewinnt','Gana el mayor'], lowerWins:['Lower wins','Niedriger gewinnt','Gana el menor'],
    roundDraw:['Draw','Remis','Empate'], roundMissing:['No point · data missing','Kein Punkt · Daten fehlen','Sin punto · faltan datos'],
    whyLeads:['Why {ticker} leads','Warum {ticker} vorn liegt','Por qué {ticker} va por delante'],
    noEdge:['No points advantage in the comparable rounds.','Kein Punktevorsprung in den vergleichbaren Runden.','Sin ventaja de puntos en los asaltos comparables.'],
    counterTitle:['An advantage for {ticker}','Ein Vorteil für {ticker}','Una ventaja para {ticker}'],
    counterGeneralTitle:['The counterargument','Der Einwand','El contraargumento'],
    counterOutside:['A useful counterpoint outside the five scored rounds.','Ein relevanter Einwand außerhalb der fünf bewerteten Runden.','Un contraargumento relevante fuera de los cinco asaltos puntuados.'],
    counterGeneral:['Price, sector economics and one-off effects still need separate review. A financial lead does not settle those questions.','Aktienpreis, Branchenökonomie und Einmaleffekte sind separat zu prüfen. Ein Finanzvorsprung beantwortet diese Fragen nicht.','El precio, la economía sectorial y los efectos extraordinarios requieren revisión aparte. Una ventaja financiera no resuelve esas cuestiones.'],
    duelLimits:['The duel judges these five reported financial ratios. Valuation and business risks need a separate assessment.','Das Duell bewertet diese fünf gemeldeten Finanzkennzahlen. Bewertung und Geschäftsrisiken benötigen eine eigene Prüfung.','El duelo evalúa estos cinco ratios financieros publicados. La valoración y los riesgos del negocio necesitan una evaluación propia.'],
    duelRules:['How the referee decides','So entscheidet der Ringrichter','Cómo decide el árbitro'],
    duelRulesText:['One point per round won, all five rounds have equal weight. Equal displayed values are draws (percentages: 1 decimal; multiples: 2). Missing figures give neither side a point. Lower net debt / EBITDA wins only with positive EBITDA; lower net dilution wins the share round.','Ein Punkt je Rundensieg; alle fünf Runden zählen gleich viel. Gleich dargestellte Werte sind remis (%: 1 Dezimalstelle; Vielfache: 2). Fehlende Werte geben keiner Seite einen Punkt. Nettoschulden / EBITDA zählen nur bei positivem EBITDA; geringere Nettoverwässerung gewinnt die Aktienrunde.','Un punto por asalto ganado, con igual peso para los cinco. Valores iguales en pantalla son empate (%: 1 decimal; múltiplos: 2). Los datos ausentes no dan puntos. Deuda neta / EBITDA solo cuenta con EBITDA positivo; menor dilución neta gana el asalto de acciones.'],
    modelScore:['InvestorAce model score · review shown separately','InvestorAce-Modellscore · Prüfstatus separat','Score del modelo InvestorAce · revisión por separado'],
    modelUnverified:['review pending','Prüfung offen','revisión pendiente'],
    duelModelNote:['A model leader requires comparable reviewed scores. Legacy totals remain historical; financial rounds use the selected fiscal year.','Ein Modellführer erfordert vergleichbare geprüfte Scores. Altwerte bleiben historisch; das Finanzduell nutzt das gewählte Geschäftsjahr.','El líder del modelo requiere scores revisados comparables. Los totales antiguos son históricos; el duelo usa el ejercicio seleccionado.'],
    rankDisagreement:['The financial duel and the InvestorAce model score favor different stocks. Valuation and other model categories can change the ranking.','Finanzduell und InvestorAce-Modellscore bevorzugen unterschiedliche Aktien. Bewertung und weitere Modellkategorien können die Rangfolge ändern.','El duelo financiero y el score de InvestorAce favorecen acciones distintas. La valoración y otras categorías del modelo pueden cambiar el ranking.'],
    duelFlag_PERIOD_MISMATCH:['Year ends are more than 183 days apart: the leader is provisional.','Die Geschäftsjahresenden liegen mehr als 183 Tage auseinander: Die Führung ist vorläufig.','Los cierres anuales distan más de 183 días: la ventaja es provisional.'],
    duelFlag_STALE_DATA:['A snapshot is older than 14 days.','Ein Daten-Snapshot ist älter als 14 Tage.','Una descarga de datos tiene más de 14 días.'],
    duelFlag_CACHED_DATA:['A failed refresh retained an earlier snapshot.','Nach einem fehlgeschlagenen Abruf wird ein früherer Snapshot verwendet.','Tras una actualización fallida se conservan datos anteriores.'],
    duelFlag_SOURCE_TIME_UNKNOWN:['A retrieval timestamp is unknown.','Ein Abrufzeitpunkt ist unbekannt.','Se desconoce una fecha de descarga.'],
    duelFlag_FUTURE_DATA:['Future-dated data is excluded from the fight.','Zukünftig datierte Daten sind vom Duell ausgeschlossen.','Se excluyen del duelo los datos con fecha futura.'],
    duelFlag_OLD_FINANCIALS:['The latest annual period is more than 550 days old.','Der letzte Jahresabschluss ist älter als 550 Tage.','El último periodo anual tiene más de 550 días.'],
    duelFlag_DATA_REVIEW:['Currency or security-type data needs review.','Währungs- oder Wertpapierdaten benötigen eine Prüfung.','La moneda o el tipo de valor requieren revisión.'],
    duelIncomplete:['Some rounds lack comparable data; the lead is provisional.','Für einige Runden fehlen vergleichbare Daten; die Führung ist vorläufig.','Faltan datos comparables en algunos asaltos; la ventaja es provisional.'],
  };
  let language = ['en','de','es'].includes(params.get('lang')) ? params.get('lang') : 'en';
  let group = 'all';
  let invalidTicker = ['a','b'].some(key => params.has(key) && !byTicker.has(params.get(key)));
  const t = key => translations[key]?.[['en','de','es'].indexOf(language)] ?? key;
  const groups = {income:'income', cash:'cashFlow', balance:'balanceSheet', shares:'shareSupply'};
  const metrics = [
    ['revenue','income','money'], ['revenue_growth','income','percent'], ['gross_profit','income','money'], ['gross_margin','income','percent'],
    ['operating_income','income','money'], ['operating_margin','income','percent'], ['ebitda','income','money'], ['net_income','income','money'], ['net_margin','income','percent'],
    ['ocf','cash','money'], ['capex','cash','money'], ['fcf','cash','money','fcfNote'], ['fcf_margin','cash','percent'], ['stock_comp','cash','money'], ['buybacks','cash','money'],
    ['cash','balance','money','cashNote'], ['debt','balance','money','debtNote'], ['net_debt','balance','money'], ['assets','balance','money'], ['liabilities','balance','money'], ['equity','balance','money'],
    ['net_debt_ebitda','balance','multiple'], ['debt_equity','balance','multiple'],
    ['shares_outstanding','shares','shares','currentNote',true], ['float_shares','shares','shares','currentNote',true], ['float_pct','shares','percent','currentNote',true],
    ['shares_basic','shares','shares','averageNote'], ['shares_diluted','shares','shares','averageNote'], ['dilution','shares','percent','dilutionNote'],
  ];
  const locale = () => ({en:'en-US',de:'de-DE',es:'es-ES'}[language]);
  const n = (value, digits=1) => new Intl.NumberFormat(locale(),{maximumFractionDigits:digits,minimumFractionDigits:digits}).format(value);
  const fmt = (value, type) => !finite(value) ? '—' : type === 'percent' ? n(value) + '%' : type === 'multiple' ? n(value,2) + '×' : n(value / 1e6);
  const date = value => value ? String(value).replace('T',' ').slice(0,19) + (String(value).includes('T') ? ' UTC' : '') : '—';
  const selected = () => [byTicker.get($('left').value), byTicker.get($('right').value)];
  const fiscal = row => row?.annual?.[Number($('period').value)] ?? {};
  const value = (row, metric) => (metric[4] ? row?.market : fiscal(row))?.[metric[0]];
  const option = row => `<option value="${esc(row.ticker)}">${esc(row.ticker)} · ${esc(row.name)}</option>`;
  const phrase = (key,ticker) => t(key).replace('{ticker}',ticker ?? '—');
  $('left').innerHTML = $('right').innerHTML = rows.map(option).join('');
  $('left').value = byTicker.has(params.get('a')) ? params.get('a') : byTicker.has('WKL') ? 'WKL' : rows[0]?.ticker ?? '';
  $('right').value = byTicker.has(params.get('b')) ? params.get('b') : byTicker.has('DIS') ? 'DIS' : rows[1]?.ticker ?? rows[0]?.ticker ?? '';
  $('language').value = language;

  function chart(row) {
    const points = [...(row.annual ?? [])].reverse().filter(a => finite(a.revenue));
    if (!points.length) return `<div class="empty-chart">${esc(t('unavailable'))}</div>`;
    const width = 350, height = 68, top = 5, base = 48;
    const maximum = Math.max(...points.map(p => Math.abs(p.revenue)),1);
    const step = width / points.length;
    return `<svg class="sparkline" viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(t('history') + ': ' + row.ticker)}">` +
      points.map((p,i) => {
        const h = Math.abs(p.revenue) / maximum * (base-top);
        const x = i*step + step*.25;
        return `<rect x="${x}" y="${base-h}" width="${step*.5}" height="${h}" rx="2" fill="var(--accent)" opacity="${.35+.65*(i+1)/points.length}"><title>${esc(p.period_end + ': ' + fmt(p.revenue,'money') + ' ' + (row.financial_currency ?? '?') + ' ' + t('millions'))}</title></rect><text x="${i*step+step*.5}" y="63" text-anchor="middle">${esc(p.period_end.slice(0,4))}</text>`;
      }).join('') + '</svg>';
  }

  function card(row, index) {
    if (!row) return '';
    const fy = fiscal(row);
    const status = {OK:'provider',PARTIAL:'partial',CACHED:'cached',UNAVAILABLE:'unavailable'}[row.status] ?? 'unavailable';
    return `<article class="stock-card ${index ? 'b' : 'a'}"><div class="card-top"><span class="ticker-label">${esc(row.ticker)}</span><span class="status ${row.status==='OK'?'':'alert'}">${esc(t(status))}</span></div><h2>${esc(row.name)}</h2><div class="card-meta">${esc(row.listing)} · ${esc(row.sector)} · ${esc(row.financial_currency ?? '?')}</div><div class="card-kpis">` +
      ['revenue','net_income','fcf'].map(key=>`<div><div class="kpi-label">${esc(t(key))}</div><div class="kpi-value">${fmt(fy[key],'money')}</div><div class="kpi-unit">${esc(row.financial_currency ?? '?')} ${esc(t('millions'))}</div></div>`).join('') +
      `</div><div class="card-date">${esc(t('fy'))}: ${esc(fy.period_end ?? t('notAvailable'))}</div><div class="spark-heading"><span>${esc(t('history'))}</span><span>${esc(t('independentScale'))}</span></div>${chart(row)}<div class="card-date">${esc(t('retrieved'))}: ${esc(date(row.retrieved_at))}</div></article>`;
  }

  function writeUrl() {
    const url = new URL(location.href);
    url.searchParams.set('a',$('left').value);
    url.searchParams.set('b',$('right').value);
    url.searchParams.set('lang',language);
    url.searchParams.set('year',$('period').value);
    try { history.replaceState(null,'',url); } catch { /* file previews may restrict history */ }
  }

  function renderDuel(chosen) {
    const result=InvestorAceDuel.judge(chosen[0],chosen[1],{period:Number($('period').value)});
    const index=result.leader==='b'?1:0;
    const leading=chosen[index];
    const title=result.status==='WINNER'?phrase('duelWinner',leading?.ticker):
      result.status==='PROVISIONAL'?phrase('duelProvisional',leading?.ticker):
      t({DRAW:'duelDraw',OPEN:'duelOpen',SAME_STOCK:'duelSame'}[result.status]);
    const fact=(round,names=false)=>`${names?esc(chosen[0]?.ticker ?? '')+' ':''}${fmt(round.left,round.unit)} <span class="duel-versus">vs</span> ${names?esc(chosen[1]?.ticker ?? '')+' ':''}${fmt(round.right,round.unit)}`;
    const wins=result.rounds.filter(r=>r.winner===result.leader);
    const why=result.leader ? wins.map(round=>`<li><strong>${esc(t(round.label))}</strong><span>${fact(round)} · ${esc(t(round.direction>0?'higherWins':'lowerWins'))}</span></li>`).join('') : `<li>${esc(t('noEdge'))}</li>`;
    const counter=result.counterargument;
    const counterStock=counter?.side==='a'?chosen[0]:chosen[1];
    const counterText=counter ? `<strong>${esc(t(counter.metric))}</strong><p>${fact(counter,true)} · ${esc(t(counter.direction>0?'higherWins':'lowerWins'))}</p>${counter.outsideRounds?`<small>${esc(t('counterOutside'))}</small>`:''}` : `<p>${esc(t('counterGeneral'))}</p>`;
    const notes=[...result.flags.map(flag=>t('duelFlag_'+flag))];
    if (result.missing) notes.unshift(t('duelIncomplete'));
    $('duel').dataset.status=result.status;
    $('duel').dataset.winner=result.winner ? chosen[result.winner==='a'?0:1]?.ticker ?? '' : '';
    $('duel').innerHTML=`<div class="duel-head"><div><div class="eyebrow">${esc(t('duelEyebrow'))}</div><h2>${esc(t('duelTitle'))}</h2></div><span class="duel-rule-tag">${esc(t('duelRuleShort'))}</span></div>
      <div class="duel-fighters">${chosen.map((row,i)=>`${i?'<div class="duel-vs" aria-hidden="true">VS</div>':''}<div class="duel-fighter ${i?'b':'a'} ${result.winner===(i?'b':'a')?'champion':''}"><div class="fighter-info"><span class="fighter-corner">${i?'B':'A'}</span><strong>${esc(row?.ticker ?? '—')}</strong><span class="fighter-name">${esc(row?.name ?? '')}</span><small class="fighter-date">${esc(fiscal(row).period_end ?? '—')}</small></div><span class="fighter-points" data-duel-points="${i?'b':'a'}">${i?result.rightPoints:result.leftPoints}</span></div>`).join('')}</div>
      <div class="duel-result ${result.status==='WINNER'?'decided':''}" role="status" aria-live="polite"><span class="duel-medal" aria-hidden="true">${result.status==='WINNER'?'★':'◇'}</span><div><h3 id="duel-verdict">${esc(title)}</h3><p>${5-result.missing}/5 ${esc(t('comparableRounds'))} · ${result.tied} ${esc(t('drawnRounds'))}</p></div></div>
      <div class="duel-rounds" role="list">${result.rounds.map((round,i)=>`<div class="duel-round" role="listitem" data-duel-round="${round.metric}"><div class="round-label"><span class="round-number">${String(i+1).padStart(2,'0')}</span><div><strong>${esc(t(round.label))}</strong><small>${esc(t(round.metric))} · ${esc(t(round.direction>0?'higherWins':'lowerWins'))}</small></div></div><span class="round-value a ${round.winner==='a'?'round-win':''}">${fmt(round.left,round.unit)}</span><span class="round-call ${round.winner}">${round.winner==='a'||round.winner==='b'?esc(chosen[round.winner==='a'?0:1]?.ticker ?? '')+' +1':esc(t(round.winner==='tie'?'roundDraw':'roundMissing'))}</span><span class="round-value b ${round.winner==='b'?'round-win':''}">${fmt(round.right,round.unit)}</span></div>`).join('')}</div>
      <div class="duel-explanation"><div class="duel-why"><h3>${esc(result.leader?phrase('whyLeads',leading?.ticker):t('financials'))}</h3><p class="duel-fact-order">${esc(chosen[0]?.ticker ?? '—')} <span class="duel-versus">vs</span> ${esc(chosen[1]?.ticker ?? '—')}</p><ul>${why}</ul></div><aside class="duel-counter"><h3>${esc(counter?phrase('counterTitle',counterStock?.ticker):t('counterGeneralTitle'))}</h3>${counterText}<p class="duel-limit">${esc(t('duelLimits'))}</p></aside></div>
      ${notes.length?`<div class="duel-notes">${notes.map(note=>`<p>${esc(note)}</p>`).join('')}</div>`:''}
      ${result.rankDisagreement?`<p class="duel-rank-disagreement">${esc(t('rankDisagreement'))}</p>`:''}
      <div class="duel-model"><strong>${esc(t('modelScore'))}</strong><div>${chosen.map(row=>`<span>${esc(row?.ticker ?? '—')} <b>${finite(row?.model?.score)?n(row.model.score,2)+'/10':'—'}</b>${row?.model?.review_required?` <small>${esc(t('modelUnverified'))}</small>`:''}</span>`).join('')}</div><p>${esc(t('duelModelNote'))}</p><small>${esc(t('snapshot'))}: ${esc(date(chosen[0]?.model?.captured_at))}</small></div>
      <details class="duel-rules"><summary>${esc(t('duelRules'))}</summary><p>${esc(t('duelRulesText'))}</p></details>`;
    $('duel').setAttribute('aria-label',t('duelEyebrow'));
    return result;
  }

  function render() {
    refreshAssessments();
    const chosen = selected();
    renderDuel(chosen);
    $('universe-count').textContent = data.universe_count;
    $('stock-cards').innerHTML = chosen.map(card).join('');
    const warnings = [];
    if (invalidTicker) warnings.push(t('universeOnly').replace('76',String(data.universe_count)));
    if (chosen[0] && chosen[0]===chosen[1]) warnings.push(t('sameStock'));
    if (chosen.every(Boolean)) {
      const currencies = chosen.map(r => r.financial_currency);
      if (currencies[0] && currencies[1] && currencies[0]!==currencies[1]) warnings.push(t('currencyWarning'));
      const dates = chosen.map(r => fiscal(r).period_end);
      if (dates[0] && dates[1] && dates[0]!==dates[1]) warnings.push(t('dateWarning'));
    }
    if (chosen.some(r => !r || !fiscal(r).period_end)) warnings.push(t('missingWarning'));
    chosen.forEach(r => {
      if (!r) return;
      (r.warnings ?? []).forEach(w => warnings.push(r.ticker + ': ' + t(w)));
      const age = (Date.now()-Date.parse(r.retrieved_at))/86400000;
      if (age > 14) warnings.push(r.ticker + ': ' + t('stale'));
    });
    $('warnings').innerHTML = [...new Set(warnings)].map(w=>`<div class="warning">${esc(w)}</div>`).join('');
    $('metric-head').innerHTML = `<tr><th>${esc(t('metric'))}</th>`+chosen.map(r=>`<th>${esc(r?.ticker ?? '—')}<small>${esc(r?.financial_currency ?? '?')} · ${esc(fiscal(r).period_end ?? '—')}</small></th>`).join('')+'</tr>';
    let previous = '';
    $('metric-rows').innerHTML = metrics.filter(m=>group==='all'||m[1]===group).map(m=>{
      let heading = '';
      if (previous!==m[1]) { previous=m[1]; heading=`<tr class="group-row"><td colspan="3">${esc(t(groups[m[1]]))}</td></tr>`; }
      return heading + `<tr data-metric="${m[0]}"><td>${esc(t(m[0]))}${m[3]?`<small>${esc(t(m[3]))}</small>`:''}</td>`+
        chosen.map(r=>{
          const v = value(r,m);
          const unit = m[2]==='money' ? `${r?.financial_currency ?? '?'} ${t('millions')}` : m[2]==='shares' ? t('millions') : '';
          const timing = m[4] ? `${t('retrieved')}: ${date(r?.market?.retrieved_at)}` : '';
          return `<td${finite(v)?'':' class="missing"'}>${fmt(v,m[2])}${unit?`<small>${esc(unit)}</small>`:''}${timing?`<small>${esc(timing)}</small>`:''}</td>`;
        }).join('')+'</tr>';
    }).join('');
    $('sources').innerHTML = chosen.map(r=>`<div><h3>${esc(r?.ticker ?? '')} · ${esc(t('source'))}</h3>`+(r?.sources ?? []).filter(s=>typeof s.url==='string'&&s.url.startsWith('https://finance.yahoo.com/')).map(s=>`<a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.label)} ↗</a>`).join('')+'</div>').join('');
    $('snapshot-time').textContent = t('snapshot') + ': ' + date(data.snapshot_at);
    $('export').disabled = !chosen.every(Boolean);
    writeUrl();
  }

  function localize() {
    document.documentElement.lang=language;
    document.title='InvestorAce · '+t('compare');
    document.querySelectorAll('[data-i18n]').forEach(el=>{el.textContent=t(el.dataset.i18n);});
    const period = $('period').value || (['0','1','2','3'].includes(params.get('year')) ? params.get('year') : '0');
    $('period').innerHTML = ['latestFY','priorFY','twoFY','threeFY'].map((key,i)=>`<option value="${i}">${esc(t(key))}</option>`).join('');
    $('period').value=period;
    $('left').setAttribute('aria-label',t('firstStock'));
    $('right').setAttribute('aria-label',t('secondStock'));
    $('period').setAttribute('aria-label',t('period'));
    $('scoreboard-link').href=language==='en'?'index.html':`index.${language}.html`;
    render();
  }

  ['left','right','period'].forEach(id=>$(id).addEventListener('change',()=>{invalidTicker=false;render();}));
  $('language').addEventListener('change',()=>{language=$('language').value;localize();});
  $('swap').addEventListener('click',()=>{const a=$('left').value;$('left').value=$('right').value;$('right').value=a;invalidTicker=false;render();});
  document.querySelectorAll('[data-group]').forEach(button=>button.addEventListener('click',()=>{
    group=button.dataset.group;
    document.querySelectorAll('[data-group]').forEach(b=>{b.classList.toggle('selected',b===button);b.setAttribute('aria-pressed',String(b===button));});
    render();
  }));
  $('share').addEventListener('click',async()=>{
    try {await navigator.clipboard.writeText(location.href);$('announcements').textContent=t('copied');$('share').textContent=t('copied');}
    catch {$('announcements').textContent=location.href;window.prompt(t('share'),location.href);}
  });
  $('export').addEventListener('click',()=>{
    refreshAssessments();
    const chosen=selected();
    const csvCell = v => '"'+(finite(v) ? String(v) : String(v ?? '').replace(/^[=+@\-\t\r]/,"'$&")).replace(/"/g,'""')+'"';
    const header=['metric','unit',...chosen.flatMap(r=>[r.ticker,r.ticker+'_period',r.ticker+'_retrieved_at'])];
    const lines=[header,...metrics.filter(m=>group==='all'||m[1]===group).map(m=>[
      t(m[0]),m[2]==='money'?'reporting currency (base units)':m[2]==='shares'?'shares':m[2]==='percent'?'%':'x',
      ...chosen.flatMap(r=>[value(r,m),m[4]?'provider snapshot':fiscal(r).period_end,m[4]?r.market?.retrieved_at:r.retrieved_at])
    ])];
    lines.push(['financial_currency','',...chosen.flatMap(r=>[r.financial_currency,'',''])]);
    const duel=InvestorAceDuel.judge(chosen[0],chosen[1],{period:Number($('period').value)});
    lines.push(['duel_round_wins','points',duel.leftPoints,fiscal(chosen[0]).period_end,chosen[0].retrieved_at,
      duel.rightPoints,fiscal(chosen[1]).period_end,chosen[1].retrieved_at]);
    lines.push(['duel_status',duel.policy,duel.status,'','',duel.status,'','']);
    const content='\uFEFF'+lines.map(line=>line.map(csvCell).join(',')).join('\r\n');
    const url=URL.createObjectURL(new Blob([content],{type:'text/csv;charset=utf-8'}));
    const link=document.createElement('a');link.href=url;link.download=`InvestorAce_${chosen.map(r=>r.ticker).join('_vs_')}.csv`;
    link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  localize();
  InvestorAceAssessment.watch(render,[...frozenAssessments.values()]);
})();
