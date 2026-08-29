// InvestorAce ticker library · corrected
// Fixes over the previous version:
//   NVO      cur DKK -> USD   (NYSE ADR. The DKK line is NOVO-B.CO)
//   ENB      cur CAD -> ENB.TO, since plain ENB is the NYSE line and quotes USD
//   MUVG.DE  -> MUV2.DE       (MUVG.DE does not exist)
//   IBST     -> IBST.L, cur GBp (London quotes pence, not pounds)
//   added ENG.MC (Enagas). ENGI.PA is ENGIE — a different company entirely.
const tickerLibrary = [
 // GROWTH
 {yf:"NVDA",name:"NVIDIA",index:"NASDAQ",group:"Growth",sector:"Semis",cur:"USD"},
 {yf:"MSFT",name:"Microsoft",index:"NASDAQ",group:"Growth",sector:"Software",cur:"USD"},
 {yf:"AMZN",name:"Amazon",index:"NASDAQ",group:"Growth",sector:"Consumer Disc",cur:"USD"},
 {yf:"GOOGL",name:"Alphabet",index:"NASDAQ",group:"Growth",sector:"Communication",cur:"USD"},
 {yf:"META",name:"Meta Platforms",index:"NASDAQ",group:"Growth",sector:"AdTech",cur:"USD"},
 {yf:"AMD",name:"Advanced Micro Devices",index:"NASDAQ",group:"Growth",sector:"Semis",cur:"USD"},
 {yf:"PLTR",name:"Palantir",index:"S&P 500",group:"Growth",sector:"Software",cur:"USD"},
 {yf:"CRWD",name:"CrowdStrike",index:"NASDAQ",group:"Growth",sector:"Software",cur:"USD"},
 {yf:"NOW",name:"ServiceNow",index:"S&P 500",group:"Growth",sector:"Software",cur:"USD"},
 {yf:"ADBE",name:"Adobe",index:"NASDAQ",group:"Growth",sector:"Software",cur:"USD"},
 {yf:"ONON",name:"On Holding",index:"NYSE",group:"Growth",sector:"Apparel",cur:"USD"},
 {yf:"UBER",name:"Uber Technologies",index:"S&P 500",group:"Growth",sector:"Platform",cur:"USD"},
 {yf:"ISRG",name:"Intuitive Surgical",index:"S&P 500",group:"Growth",sector:"MedTech",cur:"USD"},
 {yf:"MELI",name:"MercadoLibre",index:"NASDAQ",group:"Growth",sector:"Platform",cur:"USD"},
 // DEFENSIVE
 {yf:"JNJ",name:"Johnson & Johnson",index:"Dow",group:"Defensive",sector:"Pharma",cur:"USD"},
 {yf:"PG",name:"Procter & Gamble",index:"Dow",group:"Defensive",sector:"Staples",cur:"USD"},
 {yf:"KO",name:"Coca-Cola",index:"Dow",group:"Defensive",sector:"Staples",cur:"USD"},
 {yf:"PEP",name:"PepsiCo",index:"S&P 500",group:"Defensive",sector:"Staples",cur:"USD"},
 {yf:"COST",name:"Costco",index:"S&P 500",group:"Defensive",sector:"Retail",cur:"USD"},
 {yf:"ABT",name:"Abbott Laboratories",index:"S&P 500",group:"Defensive",sector:"MedTech",cur:"USD"},
 {yf:"LLY",name:"Eli Lilly",index:"S&P 500",group:"Defensive",sector:"Pharma",cur:"USD"},
 {yf:"UNH",name:"UnitedHealth",index:"Dow",group:"Defensive",sector:"Health Ins",cur:"USD"},
 {yf:"PFE",name:"Pfizer",index:"S&P 500",group:"Defensive",sector:"Pharma",cur:"USD"},
 {yf:"SAN.PA",name:"Sanofi",index:"CAC 40",group:"Defensive",sector:"Pharma",cur:"EUR"},
 {yf:"NVO",name:"Novo Nordisk ADR",index:"NYSE",group:"Defensive",sector:"Pharma",cur:"USD"},
 {yf:"NESN.SW",name:"Nestle",index:"SMI",group:"Defensive",sector:"Staples",cur:"CHF"},
 {yf:"ROG.SW",name:"Roche Holding",index:"SMI",group:"Defensive",sector:"Pharma",cur:"CHF"},
 {yf:"RWE.DE",name:"RWE AG",index:"DAX",group:"Defensive",sector:"Utilities",cur:"EUR"},
 // CYCLICAL
 {yf:"CAT",name:"Caterpillar",index:"Dow",group:"Cyclical",sector:"Industrials",cur:"USD"},
 {yf:"BA",name:"Boeing",index:"Dow",group:"Cyclical",sector:"Aerospace",cur:"USD"},
 {yf:"JPM",name:"JPMorgan Chase",index:"Dow",group:"Cyclical",sector:"Financials",cur:"USD"},
 {yf:"V",name:"Visa",index:"Dow",group:"Cyclical",sector:"Financials",cur:"USD"},
 {yf:"XOM",name:"Exxon Mobil",index:"Dow",group:"Cyclical",sector:"Energy",cur:"USD"},
 {yf:"AR",name:"Antero Resources",index:"NYSE",group:"Cyclical",sector:"Energy",cur:"USD"},
 {yf:"DVN",name:"Devon Energy",index:"S&P 500",group:"Cyclical",sector:"Energy",cur:"USD"},
 {yf:"CNX",name:"CNX Resources",index:"NYSE",group:"Cyclical",sector:"Energy",cur:"USD"},
 {yf:"BMW.DE",name:"BMW AG",index:"DAX",group:"Cyclical",sector:"Automotive",cur:"EUR"},
 {yf:"BAS.DE",name:"BASF SE",index:"DAX",group:"Cyclical",sector:"Materials",cur:"EUR"},
 {yf:"SIE.DE",name:"Siemens AG",index:"DAX",group:"Cyclical",sector:"Industrials",cur:"EUR"},
 {yf:"AIR.PA",name:"Airbus SE",index:"CAC 40",group:"Cyclical",sector:"Aerospace",cur:"EUR"},
 {yf:"SAN.MC",name:"Banco Santander",index:"IBEX 35",group:"Cyclical",sector:"Financials",cur:"EUR"},
 {yf:"IBST.L",name:"Ibstock plc",index:"FTSE 250",group:"Cyclical",sector:"Materials",cur:"GBp"},
 // SENSITIVE
 {yf:"AVGO",name:"Broadcom",index:"S&P 500",group:"Sensitive",sector:"Semis",cur:"USD"},
 {yf:"INTC",name:"Intel",index:"Dow",group:"Sensitive",sector:"Semis",cur:"USD"},
 {yf:"ORCL",name:"Oracle",index:"S&P 500",group:"Sensitive",sector:"Software",cur:"USD"},
 {yf:"CRM",name:"Salesforce",index:"Dow",group:"Sensitive",sector:"Software",cur:"USD"},
 {yf:"DIS",name:"Walt Disney",index:"Dow",group:"Sensitive",sector:"Media",cur:"USD"},
 {yf:"CMCSA",name:"Comcast",index:"S&P 500",group:"Sensitive",sector:"Media",cur:"USD"},
 {yf:"SAP.DE",name:"SAP SE",index:"DAX",group:"Sensitive",sector:"Software",cur:"EUR"},
 {yf:"IFX.DE",name:"Infineon",index:"DAX",group:"Sensitive",sector:"Semis",cur:"EUR"},
 {yf:"ASML.AS",name:"ASML Holding",index:"AEX",group:"Sensitive",sector:"Semis",cur:"EUR"},
 {yf:"ADYEN.AS",name:"Adyen N.V.",index:"AEX",group:"Sensitive",sector:"Fintech",cur:"EUR"},
 // HIGH YIELD & VALUE
 {yf:"O",name:"Realty Income",index:"S&P 500",group:"High Yield",sector:"REIT",cur:"USD"},
 {yf:"VICI",name:"VICI Properties",index:"S&P 500",group:"High Yield",sector:"REIT",cur:"USD"},
 {yf:"ENB.TO",name:"Enbridge (Toronto)",index:"TSX",group:"High Yield",sector:"Midstream",cur:"CAD"},
 {yf:"ENG.MC",name:"Enagas",index:"IBEX 35",group:"High Yield",sector:"Utilities",cur:"EUR"},
 {yf:"WKL.AS",name:"Wolters Kluwer",index:"AEX",group:"High Yield",sector:"Info Svcs",cur:"EUR"},
 {yf:"MC.PA",name:"LVMH",index:"CAC 40",group:"High Yield",sector:"Luxury",cur:"EUR"},
 {yf:"ALV.DE",name:"Allianz SE",index:"DAX",group:"High Yield",sector:"Financials",cur:"EUR"},
 {yf:"MUV2.DE",name:"Munich Re",index:"DAX",group:"High Yield",sector:"Insurance",cur:"EUR"},
 {yf:"SPGI",name:"S&P Global",index:"S&P 500",group:"High Yield",sector:"Info Svcs",cur:"USD"},
 {yf:"T",name:"AT&T",index:"S&P 500",group:"High Yield",sector:"Communication",cur:"USD"}
];
