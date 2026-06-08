#!/usr/bin/env python3
"""
Build a comprehensive list of SaaS companies across all categories.
Merges existing collected data with a large curated list, deduplicates,
and saves to data/all_companies.json.
"""

import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "all_companies.json")


def load_existing():
    """Load company names from previously collected JSON files."""
    names = set()

    # crm_listings.json — list of dicts with "name" key
    crm_path = os.path.join(DATA_DIR, "crm_listings.json")
    if os.path.exists(crm_path):
        with open(crm_path) as f:
            for item in json.load(f):
                if isinstance(item, dict) and "name" in item:
                    names.add(item["name"].strip())

    # g2_seo_companies.json — list of strings
    g2_path = os.path.join(DATA_DIR, "g2_seo_companies.json")
    if os.path.exists(g2_path):
        with open(g2_path) as f:
            for item in json.load(f):
                if isinstance(item, str):
                    names.add(item.strip())

    return names


# ---------------------------------------------------------------------------
# Massive curated list organised by category
# ---------------------------------------------------------------------------

COMPANIES_BY_CATEGORY = {

    # ── CRM ────────────────────────────────────────────────────────────
    "CRM": [
        "Salesforce", "HubSpot", "Pipedrive", "Zoho CRM", "Freshsales",
        "Monday CRM", "Copper", "Insightly", "Nimble", "Keap",
        "Close", "Nutshell", "Capsule CRM", "SugarCRM", "Less Annoying CRM",
        "Agile CRM", "Vtiger", "Streak", "Bitrix24", "Apptivo",
        "Salesflare", "Teamgate", "Pipeliner CRM", "Creatio", "Zendesk Sell",
        "NetSuite CRM", "Microsoft Dynamics 365", "Oracle CRM", "SAP CRM",
        "Sage CRM", "Act!", "Maximizer CRM", "Daylite", "Highrise",
        "Contactually", "Redtail CRM", "Wealthbox", "Practifi",
        "Jungo", "Shape Software", "IXACT Contact", "Follow Up Boss",
        "LionDesk", "Wise Agent", "Propertybase", "kvCORE", "BoomTown",
        "Real Geeks", "Chime", "Sierra Interactive",
        "LeadSquared", "Freshworks CRM", "Engagebay", "Ontraport",
        "GreenRope", "OroCRM", "1CRM", "EspoCRM", "Odoo CRM",
        "Zurmo", "CiviCRM", "SuiteCRM", "YetiForce", "Cloze",
        "Membrain", "Spiro", "Veloxy", "Revegy", "Upland Altify",
        "DealHub", "People.ai", "Troops", "Scratchpad",
        "Dooly", "Groove", "Mixmax", "Yesware", "Cirrus Insight",
        "Ebsta", "Affinity", "4Degrees", "Introhive", "DemandFarm",
        "Kapta", "Planhat", "SmartKarrot", "ClientSuccess", "Gainsight",
    ],

    # ── Project Management ─────────────────────────────────────────────
    "Project Management": [
        "Asana", "Monday.com", "ClickUp", "Jira", "Trello",
        "Wrike", "Smartsheet", "Basecamp", "Notion", "Teamwork",
        "Airtable", "Podio", "Workfront", "Coda", "Hive",
        "Nifty", "Paymo", "Toggl Plan", "MeisterTask", "ProofHub",
        "Freedcamp", "Zoho Projects", "LiquidPlanner", "Workzone", "Celoxis",
        "ProjectManager.com", "Aha!", "Productboard", "Shortcut", "Linear",
        "Height", "Plane", "Zenhub", "Backlog", "Taiga",
        "OpenProject", "Redmine", "YouTrack", "Targetprocess", "Planview",
        "Clarizen", "Mavenlink", "Kantata", "Forecast", "Scoro",
        "Birdview PSA", "BigTime", "Accelo", "Ravetree", "Function Point",
        "Harvest Forecast", "Float", "Resource Guru", "Hub Planner", "Runn",
        "Mosaic", "Saviom", "Tempus Resource", "Parallax", "Retain",
        "Confluence", "Slite", "Nuclino", "Slab", "Almanac",
        "Craft", "Saga", "Clover", "Taskade", "Quire",
        "Stackby", "Whimsical", "Miro", "FigJam", "Lucidspark",
        "Conceptboard", "Stormboard", "MURAL", "Creately", "Cacoo",
    ],

    # ── Marketing Automation ───────────────────────────────────────────
    "Marketing Automation": [
        "Mailchimp", "ActiveCampaign", "Marketo", "Pardot", "Eloqua",
        "HubSpot Marketing Hub", "Klaviyo", "Brevo", "Customer.io", "Drip",
        "ConvertKit", "GetResponse", "Omnisend", "Iterable", "Braze",
        "Sailthru", "Emarsys", "Acoustic", "Bloomreach", "Dotdigital",
        "Ortto", "Autopilot", "SharpSpring", "Act-On", "Keap",
        "Ontraport", "EngageBay", "Mautic", "SendPulse", "Moosend",
        "MailerLite", "AWeber", "Benchmark Email", "Constant Contact",
        "Campaign Monitor", "Emma", "Mailjet", "SparkPost", "SendGrid",
        "Postmark", "Amazon SES", "Mandrill", "Sendy", "Listmonk",
        "Sender.net", "Privy", "Justuno", "OptinMonster", "Sumo",
        "Unbounce", "Instapage", "Leadpages", "ClickFunnels", "Landingi",
        "Swipe Pages", "Carrd", "Wishpond", "ShortStack", "Woorise",
        "ReferralCandy", "Friendbuy", "Mention Me", "Extole", "Ambassador",
        "Talkable", "Referral Rock", "InviteReferrals", "GrowSurf", "Viral Loops",
        "Leanplum", "CleverTap", "MoEngage", "WebEngage", "Netcore",
        "Pushwoosh", "OneSignal", "Airship", "Kumulos", "Batch",
    ],

    # ── HR / HRIS ──────────────────────────────────────────────────────
    "HR/HRIS": [
        "Workday", "BambooHR", "Rippling", "Gusto", "ADP",
        "Paychex", "Paylocity", "Paycom", "UKG", "Ceridian",
        "SAP SuccessFactors", "Oracle HCM Cloud", "Namely", "Zenefits",
        "Personio", "Bob (HiBob)", "Lattice", "15Five", "Culture Amp",
        "Leapsome", "Reflektive", "Betterworks", "Kazoo", "Motivosity",
        "Bonusly", "Kudos", "Nectar HR", "Assembly", "Officevibe",
        "TINYpulse", "Peakon", "Glint", "Qualtrics EmployeeXM",
        "Humu", "Perceptyx", "Limeade", "Virgin Pulse", "Wellable",
        "GoTo Wellbeing", "Gympass", "ClassPass Corporate", "Headspace for Work",
        "Calm Business", "Spring Health", "Lyra Health", "Modern Health",
        "Ginger", "Talkspace for Business", "BetterUp",
        "Deel", "Remote.com", "Oyster HR", "Papaya Global", "Velocity Global",
        "Globalization Partners", "Omnipresent", "Lano", "Multiplier", "Skuad",
        "Pilot", "Letsdeel", "Remofirst", "WorkMotion", "Airbase",
        "PeopleHR", "CakeHR (Sage HR)", "Factorial", "Sesame HR", "Kenjo",
        "Charlie HR", "Breathe HR", "Natural HR", "Employment Hero", "KeyPay",
        "Eddy", "GoCo", "Homebase", "When I Work", "Deputy",
        "Sling", "7shifts", "Shiftboard", "Humanity", "Quinyx",
        "Planday", "Rotacloud", "Fourth", "Harri", "Workforce.com",
    ],

    # ── Accounting / Finance ───────────────────────────────────────────
    "Accounting/Finance": [
        "QuickBooks", "Xero", "FreshBooks", "Wave", "Sage Intacct",
        "NetSuite", "SAP Business One", "ZohoBooks", "Kashoo", "FreeAgent",
        "Patriot Software", "AccountEdge", "Manager.io", "Akaunting",
        "ZipBooks", "Hurdlr", "Bonsai", "Bench", "Pilot Bookkeeping",
        "Botkeeper", "Bookkeeper360", "Paro", "Kruze Consulting",
        "Bill.com", "Melio", "Tipalti", "AvidXchange", "Coupa",
        "SAP Ariba", "Jaggaer", "GEP", "Ivalua", "Procurify",
        "Precoro", "Kissflow Procurement", "ProcurePort", "Tradogram",
        "Spendesk", "Divvy", "Brex", "Ramp", "Airbase",
        "Center", "Navan (TripActions)", "SAP Concur", "Emburse",
        "Expensify", "Abacus", "Fyle", "Zoho Expense", "Rydoo",
        "Lola.com", "TravelPerk", "TripIt", "Egencia",
        "Chargebee", "Recurly", "Zuora", "Maxio (SaaSOptics + Chargify)",
        "Paddle", "FastSpring", "2Checkout (Verifone)", "Stripe Billing",
        "RevenueHero", "Baremetrics", "ProfitWell", "ChartMogul", "Chartio",
        "Mosaic Tech", "Jirav", "Planful", "Anaplan", "Adaptive Insights",
        "Vena Solutions", "Datarails", "Cube Software", "Abacum",
        "Pigment", "Causal", "Runway Financial", "Finmark", "Pry",
        "LivePlan", "Liveflow", "Fathom", "Spotlight Reporting", "Syft Analytics",
        "Float Cash Flow", "Fluidly", "Cashflow Manager", "Pulse",
    ],

    # ── Help Desk / Customer Support ───────────────────────────────────
    "Help Desk/Customer Support": [
        "Zendesk", "Freshdesk", "Intercom", "Helpscout", "Kayako",
        "LiveAgent", "Zoho Desk", "HappyFox", "Jitbit Helpdesk", "osTicket",
        "Spiceworks", "SysAid", "ManageEngine ServiceDesk Plus",
        "BMC Helix ITSM", "ServiceNow", "Ivanti", "Cherwell",
        "TOPdesk", "Samanage", "SolarWinds Service Desk",
        "Front", "Hiver", "Drag", "Missive", "Helpwise",
        "Gorgias", "Richpanel", "Re:amaze", "DelightChat", "eDesk",
        "ChannelReply", "xSellco", "Kustomer", "Gladly", "Dixa",
        "Assembled", "Stella Connect", "MaestroQA", "Klaus", "Scorebuddy",
        "Playvox", "NICE inContact", "Genesys Cloud", "Five9", "Talkdesk",
        "Aircall", "Dialpad", "RingCentral Contact Center", "8x8 Contact Center",
        "Vonage Contact Center", "CloudTalk", "JustCall", "PhoneBurner",
        "Callrail", "Invoca", "Marchex", "DialogTech",
        "Tidio", "LiveChat", "Olark", "Crisp", "Drift",
        "Freshchat", "Userlike", "Chatwoot", "Tawk.to", "JivoChat",
        "Chatra", "Smartsupp", "Pure Chat", "Comm100", "Zoho SalesIQ",
        "Acquire", "Podium", "Birdeye", "Reputation.com", "Yotpo",
        "Trustpilot", "Reviews.io", "Stamped.io", "Judge.me", "Feefo",
    ],

    # ── Ecommerce ──────────────────────────────────────────────────────
    "Ecommerce": [
        "Shopify", "BigCommerce", "WooCommerce", "Magento (Adobe Commerce)",
        "Wix eCommerce", "Squarespace Commerce", "Volusion", "3dcart (Shift4Shop)",
        "PrestaShop", "OpenCart", "Ecwid", "Big Cartel", "Sellfy",
        "Gumroad", "Lemon Squeezy", "Podia", "Thinkific Commerce",
        "Samcart", "ThriveCart", "Kartra", "Kajabi", "Teachable Commerce",
        "Saleor", "Medusa", "Spree Commerce", "Solidus", "Sylius",
        "Commercetools", "Elastic Path", "Fabric", "BigCommerce B2B",
        "OroCommerce", "Sana Commerce", "Mirakl", "Marketplacer",
        "Sharetribe", "Arcadier", "CS-Cart Multi-Vendor",
        "Shopware", "Lightspeed", "Vend (by Lightspeed)", "Square Online",
        "Toast", "Clover", "Revel Systems", "TouchBistro",
        "ShipStation", "ShipBob", "Shippo", "EasyPost", "Easyship",
        "Flexport", "Deliverr", "ShipHero", "SkuVault", "Cin7",
        "TradeGecko (QuickBooks Commerce)", "Ordoro", "Linnworks", "ChannelAdvisor",
        "Feedonomics", "GoDataFeed", "DataFeedWatch", "Channable",
        "Sellbrite", "Listing Mirror", "Zentail", "SellerCloud",
        "Jungle Scout", "Helium 10", "Viral Launch", "AMZScout",
        "SellerApp", "Perpetua", "Teikametrics", "Pacvue", "Skai (Kenshoo)",
        "Avalara", "TaxJar", "Vertex", "Sovos", "CertCapture",
        "Yotpo", "Stamped.io", "Loox", "Okendo", "Fera",
        "Klaviyo", "Privy", "Justuno", "Recart", "Attentive",
        "Postscript", "SMSBump", "Omnisend", "Drip", "Retention.com",
    ],

    # ── Video / Webinar ────────────────────────────────────────────────
    "Video/Webinar": [
        "Zoom", "Loom", "Vidyard", "Wistia", "Vimeo",
        "Brightcove", "Kaltura", "Panopto", "Dacast", "JW Player",
        "SproutVideo", "Cincopa", "Spotlightr", "Dubb", "BombBomb",
        "Hippo Video", "Covideo", "Bonjoro", "Soapbox", "Sendspark",
        "Pitchlane", "Tavus", "Synthesia", "Colossyan", "HeyGen",
        "D-ID", "Elai.io", "Hour One", "DeepBrain AI", "Rephrase.ai",
        "Pictory", "InVideo", "Descript", "Kapwing", "Canva Video",
        "Clipchamp", "WeVideo", "Animoto", "Biteable", "Powtoon",
        "Vyond", "Toonly", "Renderforest", "Promo.com", "Wave.video",
        "Veed.io", "FlexClip", "ScreenPal (Screencast-O-Matic)",
        "Camtasia", "OBS Studio", "Riverside.fm", "StreamYard", "Restream",
        "GoTo Webinar", "Demio", "Livestorm", "WebinarJam", "EverWebinar",
        "WebinarGeek", "BigMarker", "Airmeet", "Hopin", "Run The World",
        "Welcome (Bizzabo)", "Goldcast", "Hubilo", "ON24", "WorkCast",
        "Cvent", "Whova", "Swapcard", "Brella", "Grip",
        "Attendease", "Splash", "Bizzabo", "Eventbrite",
        "Cloudinary", "Imgix", "Uploadcare", "Filestack", "ImageKit",
        "Mux", "api.video", "Fastly (Signal Sciences)", "Agora",
        "Twilio Video", "Vonage Video API", "Daily.co", "Whereby",
        "Jitsi", "BigBlueButton", "LiveKit",
    ],

    # ── SEO / Marketing Tools ──────────────────────────────────────────
    "SEO/Marketing": [
        "Semrush", "Ahrefs", "Moz", "SE Ranking", "Serpstat",
        "Ubersuggest", "Mangools", "SpyFu", "SimilarWeb", "BrightEdge",
        "Conductor", "seoClarity", "Botify", "Lumar (DeepCrawl)", "Screaming Frog",
        "Sitebulb", "ContentKing", "Little Warden", "Ryte", "Searchmetrics",
        "RankMath", "Yoast SEO", "All in One SEO", "Surfer SEO", "Clearscope",
        "MarketMuse", "Frase", "Dashword", "WriterZen", "NeuronWriter",
        "Page Optimizer Pro", "Outranking", "GrowthBar", "Diib", "Nightwatch",
        "AccuRanker", "SERPWatcher", "Pro Rank Tracker", "Rank Ranger",
        "Advanced Web Ranking", "Wincher", "AuthorityLabs", "Nozzle", "Stat",
        "BrightLocal", "Whitespark", "Moz Local", "Yext", "Uberall",
        "SOCi", "Chatmeter", "Rio SEO", "Brandify", "Advice Local",
        "Synup", "Birdeye", "Podium", "Reputation.com", "Grade.us",
        "LocalFalcon", "GeoRanker", "Local Viking", "GMBspy",
        "Majestic", "Link Research Tools", "Monitor Backlinks", "CognitiveSEO",
        "Linkody", "SE Ranking Link Monitoring", "Pitchbox", "BuzzStream",
        "Respona", "Hunter.io", "Snov.io", "Voila Norbert", "FindThatLead",
        "LinkHunter", "Postaga", "NinjaOutreach", "GroupHigh", "Traackr",
        "BuzzSumo", "Brand24", "Mention", "Meltwater", "Cision",
        "Critical Mention", "Brandwatch", "Sprout Social", "Hootsuite", "Buffer",
    ],

    # ── Analytics ──────────────────────────────────────────────────────
    "Analytics": [
        "Mixpanel", "Amplitude", "Heap", "Google Analytics", "Matomo",
        "Plausible", "Fathom Analytics", "Simple Analytics", "GoatCounter",
        "Umami", "PostHog", "Pendo", "FullStory", "Hotjar",
        "Crazy Egg", "Lucky Orange", "Mouseflow", "Smartlook", "LogRocket",
        "Quantum Metric", "Contentsquare", "Glassbox", "Decibel (Medallia)",
        "Heap", "Indicative", "Keen IO", "Countly", "Flurry",
        "AppsFlyer", "Adjust", "Branch", "Kochava", "Singular",
        "Tenjin", "GameAnalytics", "deltaDNA", "Leanplum",
        "Segment", "mParticle", "Rudderstack", "Tealium", "Snowplow",
        "Lytics", "BlueConic", "Treasure Data", "Amperity", "ActionIQ",
        "Zeotap", "Hightouch", "Census", "Fivetran", "Stitch",
        "Airbyte", "Hevo Data", "Matillion", "Rivery", "Portable",
        "Supermetrics", "Funnel.io", "Adverity", "Improvado", "Whatagraph",
        "Databox", "Klipfolio", "Geckoboard", "Cyfe", "DashThis",
        "AgencyAnalytics", "Swydo", "ReportGarden", "NinjaCat", "TapClicks",
        "Domo", "Sisense", "Mode Analytics", "Redash", "Metabase",
        "Apache Superset", "Preset", "Holistics", "Count", "Lightdash",
        "GoodData", "Toucan Toco", "Cumul.io", "Reveal", "Luzmo",
    ],

    # ── Communication / Collaboration ──────────────────────────────────
    "Communication/Collaboration": [
        "Slack", "Microsoft Teams", "Zoom", "Google Workspace", "Webex",
        "Discord", "Mattermost", "Rocket.Chat", "Element (Matrix)", "Flock",
        "Twist", "Pumble", "Chanty", "Ryver", "Glip (RingCentral)",
        "Workplace from Meta", "Yammer (Viva Engage)", "Jostle", "Staffbase",
        "Beekeeper", "Connecteam", "Blink", "Workvivo", "Simpplr",
        "Firstup (Dynamic Signal)", "SocialChorus", "Poppulo", "Appspace",
        "ScreenCloud", "Yodeck", "Rise Vision", "Four Winds Interactive",
        "Dropbox", "Box", "Google Drive", "OneDrive", "SharePoint",
        "Egnyte", "Tresorit", "SpiderOak", "Sync.com", "pCloud",
        "Nextcloud", "ownCloud", "Seafile", "FileCloud", "Citrix ShareFile",
        "WeTransfer", "Hightail", "SendAnywhere", "Filemail",
        "Calendly", "Cal.com", "SavvyCal", "YouCanBookMe", "Acuity Scheduling",
        "Doodle", "When2meet", "Rally", "Clockwise", "Reclaim.ai",
        "Motion", "Sunsama", "Akiflow", "Morgen", "Fantastical",
        "Loom", "Vidyard", "Soapbox", "Berrycast", "Zight (CloudApp)",
        "Snagit", "Droplr", "Gyazo", "ShareX", "Jumpshare",
    ],

    # ── Design ─────────────────────────────────────────────────────────
    "Design": [
        "Figma", "Canva", "InVision", "Sketch", "Adobe XD",
        "Framer", "Webflow", "Balsamiq", "Axure", "Proto.io",
        "Marvel", "Origami Studio", "Principle", "Flinto", "ProtoPie",
        "Justinmind", "Mockplus", "UXPin", "Penpot", "Lunacy",
        "Zeplin", "Avocode", "Sympli", "Abstract", "Plant",
        "Brandfolder", "Bynder", "Canto", "Frontify", "Brandfetch",
        "Lottie (Airbnb)", "Rive", "SVGator", "LottieFiles",
        "Maze", "UserTesting", "Lookback", "Optimal Workshop",
        "Useberry", "UsabilityHub (Lyssna)", "Dovetail", "EnjoyHQ",
        "Notably", "Condens", "Aurelius",
        "Spline", "Vectary", "Blender", "Cinema 4D",
        "Procreate", "Affinity Designer", "CorelDRAW",
        "Pixelmator", "Photopea", "Remove.bg", "Cleanup.pictures",
        "Designify", "Looka", "Hatchful", "Tailor Brands", "Placeit",
        "Envato Elements", "Creative Market", "Shutterstock", "Adobe Stock",
        "Getty Images", "Unsplash", "Pexels",
        "Miro", "FigJam", "Whimsical", "Lucidchart", "Lucidspark",
        "Draw.io (diagrams.net)", "Creately", "Cacoo", "Gliffy", "SmartDraw",
        "Pitch", "Beautiful.ai", "Slidebean", "Tome", "Gamma",
        "Prezi", "Visme", "Piktochart", "Infogram", "Venngage",
    ],

    # ── DevOps / Developer Tools ───────────────────────────────────────
    "DevOps/Developer Tools": [
        "GitHub", "GitLab", "Bitbucket", "Docker", "Kubernetes",
        "Terraform", "Ansible", "Puppet", "Chef", "SaltStack",
        "Pulumi", "Crossplane", "AWS CDK", "Serverless Framework",
        "Vercel", "Netlify", "Render", "Railway", "Fly.io",
        "Heroku", "PlatformSH", "Cloudflare Workers", "Deno Deploy",
        "Supabase", "Firebase", "PlanetScale", "Neon", "CockroachDB",
        "Turso", "Upstash", "MongoDB Atlas", "Redis Cloud",
        "Fauna", "Hasura", "Prisma", "Drizzle",
        "Jenkins", "CircleCI", "Travis CI", "GitHub Actions", "GitLab CI",
        "Buildkite", "TeamCity", "Bamboo", "Harness", "Codefresh",
        "Argo CD", "Flux CD", "Spinnaker", "Octopus Deploy",
        "LaunchDarkly", "Split.io", "Unleash", "Flagsmith", "ConfigCat",
        "Datadog", "New Relic", "Dynatrace", "Splunk", "Elastic",
        "Grafana", "Prometheus", "Sentry", "Bugsnag", "Rollbar",
        "Honeycomb", "Lightstep", "Jaeger", "Zipkin",
        "PagerDuty", "Opsgenie", "VictorOps (Splunk On-Call)",
        "Statuspage", "Instatus", "Betteruptime", "UptimeRobot", "Pingdom",
        "Site24x7", "AppDynamics", "Catchpoint", "ThousandEyes",
        "Snyk", "Veracode", "Checkmarx", "SonarQube", "SonarCloud",
        "Codacy", "CodeClimate", "Coveralls", "Codecov",
        "JFrog Artifactory", "Nexus Repository", "Harbor", "Quay",
        "HashiCorp Vault", "CyberArk", "Thales", "BeyondTrust",
        "Retool", "Appsmith", "Budibase", "Tooljet", "Superblocks",
        "Airplane", "Internal.io", "DronaHQ", "Tremor", "Windmill",
        "Postman", "Insomnia", "Hoppscotch", "Swagger (SmartBear)",
        "ReadMe", "Stoplight", "Redocly", "API Platform",
        "Twilio", "SendGrid", "Vonage", "MessageBird", "Plivo",
        "Nylas", "Courier", "Knock", "Novu", "MagicBell",
    ],

    # ── Cybersecurity ──────────────────────────────────────────────────
    "Cybersecurity": [
        "CrowdStrike", "SentinelOne", "Okta", "Zscaler", "Palo Alto Networks",
        "Fortinet", "Check Point", "Sophos", "Trend Micro", "McAfee",
        "Norton (Gen Digital)", "Bitdefender", "Kaspersky", "ESET", "Malwarebytes",
        "Carbon Black (VMware)", "Cylance (BlackBerry)", "Cybereason", "Cynet",
        "Huntress", "Arctic Wolf", "Expel", "Red Canary", "Secureworks",
        "ReliaQuest", "Rapid7", "Qualys", "Tenable", "Tanium",
        "Wiz", "Orca Security", "Lacework", "Sysdig", "Aqua Security",
        "Prisma Cloud (Palo Alto)", "Ermetic", "Lightspin", "Sonrai Security",
        "Cloudflare", "Akamai", "Imperva", "F5 Networks", "Barracuda",
        "Proofpoint", "Mimecast", "Abnormal Security", "Material Security",
        "Tessian", "Vade Secure", "Agari", "Area 1 Security",
        "Varonis", "Rubrik", "Cohesity", "Commvault", "Veeam",
        "Druva", "Datto", "Acronis", "Carbonite", "Backblaze",
        "1Password", "LastPass", "Dashlane", "Bitwarden", "Keeper",
        "NordPass", "RoboForm", "Enpass",
        "Duo Security (Cisco)", "Ping Identity", "ForgeRock", "Auth0 (Okta)",
        "OneSpan", "Thales", "Yubico", "Hypr", "Transmit Security",
        "Recorded Future", "Mandiant (Google)", "ThreatConnect", "Anomali",
        "Intel 471", "Flashpoint", "GreyNoise", "Censys", "SecurityScorecard",
        "BitSight", "RiskRecon", "UpGuard", "Panorays", "Black Kite",
        "KnowBe4", "Proofpoint Security Awareness", "Cofense", "Infosec IQ",
        "Ninjio", "Living Security", "Hoxhunt", "Curricula", "usecure",
    ],

    # ── Sales / Revenue Intelligence ───────────────────────────────────
    "Sales/Revenue": [
        "Gong", "Outreach", "SalesLoft", "Chorus.ai (ZoomInfo)", "Clari",
        "Revenue.io", "ExecVision", "Jiminny", "Wingman (by Clari)",
        "Avoma", "Fireflies.ai", "Otter.ai", "Fathom (meetings)",
        "Grain", "tl;dv", "Krisp", "Airgram",
        "ZoomInfo", "Apollo.io", "Lusha", "Cognism", "Clearbit",
        "6sense", "Bombora", "TechTarget", "DemandScience", "LeadIQ",
        "Seamless.AI", "RocketReach", "ContactOut", "Kaspr", "Wiza",
        "Slintel (6sense)", "BuiltWith", "SimilarTech", "HG Insights",
        "Datanyze", "DiscoverOrg (ZoomInfo)", "D&B Hoovers",
        "Salesloft", "Outplay", "Reply.io", "Woodpecker", "Lemlist",
        "Instantly", "Smartlead", "Saleshandy", "Mailshake", "QuickMail",
        "GMass", "Streak", "Mixmax", "Yesware", "Lavender",
        "Regie.ai", "Copy.ai (sales)", "Jasper (sales)",
        "PandaDoc", "DocuSign", "Proposify", "Qwilr", "Better Proposals",
        "GetAccept", "DealRoom", "Aligned", "Trumpet", "Clientpoint",
        "Highspot", "Seismic", "Showpad", "Mediafly", "Bigtincan",
        "Mindtickle", "Allego", "Brainshark", "Lessonly (Seismic Learning)",
        "SalesHood", "WorkRamp", "Spekit", "WalkMe", "Whatfix",
        "Pendo", "Chameleon", "Appcues", "UserGuiding", "Userpilot",
    ],

    # ── Data / BI ──────────────────────────────────────────────────────
    "Data/BI": [
        "Tableau", "Looker", "Power BI", "Snowflake", "Databricks",
        "Qlik", "ThoughtSpot", "MicroStrategy", "TIBCO Spotfire",
        "SAP Analytics Cloud", "IBM Cognos", "Oracle Analytics",
        "Domo", "Sisense", "Mode Analytics", "Sigma Computing",
        "Redash", "Metabase", "Apache Superset", "Preset",
        "Lightdash", "Holistics", "Count", "Hex", "Observable",
        "Deepnote", "Noteable", "Databricks Notebooks", "Zeppelin",
        "dbt", "Fivetran", "Stitch", "Airbyte", "Matillion",
        "Hevo Data", "Rivery", "Portable", "CData", "SyncWith",
        "Talend", "Informatica", "Alteryx", "Trifacta (Dataprep)",
        "Paxata", "Tamr", "Dataiku", "RapidMiner", "KNIME",
        "H2O.ai", "DataRobot", "MLflow", "Weights & Biases",
        "Neptune.ai", "Comet ML", "Valohai", "Determined AI",
        "Snowplow", "Segment", "mParticle", "Rudderstack",
        "Monte Carlo", "Acceldata", "Bigeye", "Anomalo", "Atlan",
        "Alation", "Collibra", "Informatica Data Catalog", "data.world",
        "Select Star", "Castor", "Secoda", "Stemma",
        "BigQuery", "Redshift", "Synapse Analytics", "Clickhouse",
        "Druid", "Pinot", "StarRocks", "DuckDB", "MotherDuck",
    ],

    # ── Cloud Infrastructure ───────────────────────────────────────────
    "Cloud Infrastructure": [
        "AWS", "Microsoft Azure", "Google Cloud Platform", "DigitalOcean",
        "Linode (Akamai)", "Vultr", "Hetzner", "OVHcloud", "Scaleway",
        "UpCloud", "Kamatera", "Contabo", "Hostinger VPS",
        "Oracle Cloud", "IBM Cloud", "Alibaba Cloud", "Tencent Cloud",
        "Cloudflare", "Fastly", "Akamai", "StackPath", "KeyCDN",
        "BunnyCDN", "Limelight Networks", "Verizon Digital Media",
        "VMware", "Nutanix", "Proxmox", "OpenStack",
        "Red Hat OpenShift", "Rancher", "Portainer", "Mirantis",
        "Kong", "Apigee (Google)", "MuleSoft", "WSO2", "Tyk",
        "Ambassador Labs", "Traefik", "Istio", "Linkerd", "Consul",
        "Confluent (Kafka)", "Redpanda", "RabbitMQ Cloud", "PubSub+",
        "Twilio", "Vonage", "Plivo", "MessageBird", "Sinch",
        "Auth0", "Okta", "AWS Cognito", "Firebase Auth",
        "Stripe", "Adyen", "Braintree", "Square", "PayPal",
        "Contentful", "Sanity", "Strapi", "Prismic", "Storyblok",
        "Algolia", "Elasticsearch", "Typesense", "Meilisearch", "Pinecone",
        "Weaviate", "Qdrant", "ChromaDB", "Zilliz",
    ],

    # ── LMS / Education ────────────────────────────────────────────────
    "LMS/Education": [
        "Teachable", "Thinkific", "Canvas LMS", "Moodle", "Blackboard",
        "D2L Brightspace", "Schoology", "Google Classroom",
        "Kajabi", "Podia", "LearnWorlds", "Skillshare",
        "Udemy Business", "Coursera for Business", "LinkedIn Learning",
        "Pluralsight", "Codecademy", "DataCamp", "Treehouse",
        "Skilljar", "Docebo", "TalentLMS", "Absorb LMS", "iSpring",
        "360Learning", "Lessonly", "Trainual", "Knowbe4",
        "Litmos", "Cornerstone OnDemand", "SumTotal", "Saba",
        "SAP Litmos", "Bridge", "EdApp", "LearnUpon",
        "Tovuti LMS", "Academy of Mine", "EasyLMS", "SkyPrep",
        "Thought Industries", "Intellum", "WorkRamp", "Northpass",
        "Allego", "Brainshark", "MindTickle",
        "ClassDojo", "Seesaw", "Nearpod", "Pear Deck", "Kahoot!",
        "Quizlet", "Duolingo", "Babbel", "Rosetta Stone",
        "Blackbaud (K-12)", "PowerSchool", "Infinite Campus", "Tyler SIS",
        "Gradelink", "Alma", "Veracross", "FACTS", "RenWeb",
        "Ellucian", "Anthology", "Campus Management", "Jenzabar",
        "Instructure", "Echo360", "Panopto", "YuJa", "Kaltura",
    ],

    # ── Legal Tech ─────────────────────────────────────────────────────
    "Legal Tech": [
        "Clio", "LegalZoom", "DocuSign", "PandaDoc", "HelloSign (Dropbox Sign)",
        "SignNow", "Adobe Sign", "SignRequest", "Eversign", "Zoho Sign",
        "MyCase", "PracticePanther", "Smokeball", "CosmoLex", "TimeSolv",
        "Rocket Matter", "CasePacer", "Litify", "Filevine", "Needles",
        "AbacusLaw", "PCLaw", "Tabs3", "Amicus Attorney",
        "Westlaw", "LexisNexis", "Casetext", "ROSS Intelligence", "vLex",
        "Fastcase", "Ravel Law", "Docket Alarm", "Lex Machina",
        "NetDocuments", "iManage", "Worldox", "FileTrail", "Logicforce",
        "Ironclad", "Juro", "Agiloft", "ContractPodAi", "Icertis",
        "DocuSign CLM", "Evisort", "LinkSquares", "Precisely", "SpotDraft",
        "LawPay", "CPACharge", "PaySimple Legal", "Confido Legal",
        "Kira Systems", "Luminance", "Diligen", "DISCO", "Relativity",
        "Logikcull", "Nextpoint", "CloudNine", "Zapproved",
        "Thomson Reuters Legal", "Bloomberg Law", "Wolters Kluwer Legal",
        "Practical Law", "Drafting Assistant",
    ],

    # ── Real Estate Tech ───────────────────────────────────────────────
    "Real Estate Tech": [
        "Zillow", "CoStar", "AppFolio", "Buildium", "Yardi",
        "RealPage", "Entrata", "ResMan", "Rent Manager", "TenantCloud",
        "Innago", "Avail (Realtor.com)", "RentRedi", "Hemlane",
        "Stessa", "DoorLoop", "Rentec Direct", "SimplifyEm",
        "Propertyware", "MRI Software", "RealPage Analytics",
        "Apartments.com (CoStar)", "Zumper", "RentCafe", "AppFolio Property Manager",
        "kvCORE", "BoomTown", "Real Geeks", "Chime", "Sierra Interactive",
        "Follow Up Boss", "LionDesk", "Wise Agent", "Propertybase",
        "dotloop", "SkySlope", "Brokermint", "Lone Wolf Technologies",
        "zipLogix", "CTMe", "ShowingTime", "Calendly",
        "Matterport", "EyeSpy360", "Cupix", "Zillow 3D Home",
        "VirtualStaging.com", "RoOomy", "BoxBrownie", "Styldod",
        "DocuSign (real estate)", "Dotloop", "Glide", "Form Simplicity",
        "Procore (construction)", "PlanGrid", "Fieldwire", "Bluebeam",
    ],

    # ── Healthcare / MedTech SaaS ──────────────────────────────────────
    "Healthcare/MedTech": [
        "Epic Systems", "Cerner (Oracle Health)", "Athenahealth", "eClinicalWorks",
        "Allscripts", "NextGen Healthcare", "DrChrono", "Practice Fusion",
        "AdvancedMD", "Kareo", "CureMD", "Greenway Health",
        "Meditech", "CPSI", "Netsmart", "PointClickCare",
        "SimplePractice", "TherapyNotes", "Jane App", "IntakeQ",
        "Healthie", "TheraNest", "Valant", "ICANotes",
        "Doximity", "UpToDate", "Epocrates", "Medscape",
        "Veeva Systems", "Medidata (Dassault)", "IQVIA", "Flatiron Health",
        "Tempus", "Foundation Medicine", "Guardant Health",
        "Teladoc", "Amwell", "MDLive", "Doctor on Demand",
        "Doxy.me", "Vsee", "Zoom for Healthcare", "Spruce Health",
        "PatientPop", "Luma Health", "Phreesia", "Solutionreach",
        "Relatient", "NexHealth", "Weave", "Demandforce",
        "Health Catalyst", "Innovaccer", "Arcadia", "Lightbeam Health",
        "Hims & Hers", "Ro", "Nurx", "GoodRx",
        "Zocdoc", "Healthgrades", "WebMD",
        "Olive AI", "Waystar", "VisitPay", "Cedar", "Collectly",
    ],

    # ── Construction / Field Service ───────────────────────────────────
    "Construction/Field Service": [
        "Procore", "PlanGrid (Autodesk)", "Fieldwire", "Bluebeam",
        "Buildertrend", "CoConstruct", "Contractor Foreman", "Jonas Construction",
        "Sage 300 Construction", "Viewpoint Vista", "CMiC", "e-Builder",
        "Aconex (Oracle)", "Prolog (Trimble)", "InEight", "Kahua",
        "ProcoreConnect", "Autodesk Construction Cloud", "Newforma",
        "eSUB", "Raken", "busybusy", "ClockShark", "ExakTime",
        "Jobber", "ServiceTitan", "Housecall Pro", "FieldEdge",
        "ServiceMax", "Salesforce Field Service", "IFS", "Infor FSM",
        "ClickSoftware (Salesforce)", "Oracle Field Service",
        "Zuper", "Loc8", "Praxedo", "FieldPulse", "Workiz",
        "GorillaDesk", "Service Autopilot", "Real Green Systems",
        "mHelpDesk", "Freshdesk Field Service", "Dispatch",
        "Samsara", "Verizon Connect", "GPS Trackit", "KeepTruckin (Motive)",
        "Geotab", "Teletrac Navman", "CalAmp",
        "PlanSwift", "Stack", "Esticom", "ProEst", "Clear Estimates",
        "CompanyCam", "SiteCapture", "One Click LCA", "PlanRadar",
    ],

    # ── Supply Chain / Logistics ───────────────────────────────────────
    "Supply Chain/Logistics": [
        "SAP SCM", "Oracle SCM Cloud", "Blue Yonder", "Kinaxis",
        "o9 Solutions", "E2open", "Coupa Supply Chain", "JAGGAER",
        "GEP", "Ivalua", "Zycus", "Beeline", "SAP Ariba",
        "Cin7", "TradeGecko", "DEAR Inventory", "Ordoro",
        "Fishbowl", "inFlow", "Sortly", "Snelstart", "Brightpearl",
        "SkuVault", "ShipHero", "Logiwa", "3PL Central",
        "ShipStation", "ShipBob", "Shippo", "EasyPost", "Easyship",
        "Flexport", "Freightos", "project44", "FourKites",
        "MacroPoint (Descartes)", "Shippeo", "Transporeon",
        "Descartes Systems", "MercuryGate", "TMC (Trimble)", "Kuebix",
        "BluJay Solutions (E2open)", "Manhattan Associates", "Korber",
        "Locus Robotics", "6 River Systems", "Fetch Robotics",
        "Vecna Robotics", "GreyOrange", "Berkshire Grey",
        "Llamasoft (Coupa)", "Anylogic", "Optilogic",
        "Nulogy", "PackiT", "Arka", "Lumi",
        "FarEye", "DispatchTrack", "Bringg", "Onfleet", "Routific",
        "OptimoRoute", "Route4Me", "WorkWave",
    ],

    # ── Recruiting / ATS ───────────────────────────────────────────────
    "Recruiting/ATS": [
        "Greenhouse", "Lever", "Workable", "BambooHR ATS", "JazzHR",
        "Breezy HR", "Recruitee", "Teamtailor", "Ashby", "Pinpoint",
        "SmartRecruiters", "iCIMS", "Jobvite", "Oracle Taleo",
        "SAP SuccessFactors Recruiting", "Workday Recruiting",
        "ClearCompany", "Paylocity Recruiting", "Paycom Recruiting",
        "ADP Recruiting Management", "UKG Pro Recruiting",
        "Bullhorn", "Crelate", "Loxo", "Hireflow", "Gem",
        "Beamery", "Phenom", "Eightfold.ai", "Seekout", "hireEZ",
        "Entelo", "Hiretual", "Fetcher", "Celential.ai",
        "Calendly (recruiting)", "GoodTime", "ModernLoop", "Prelude",
        "HackerRank", "Codility", "CoderPad", "Qualified.io",
        "TestGorilla", "Criteria Corp", "Wonderlic", "Plum",
        "HireVue", "Spark Hire", "myInterview", "VidCruiter",
        "Brazen", "Handshake", "Symplicity", "GradLeaders",
        "Indeed", "LinkedIn Recruiter", "ZipRecruiter", "Glassdoor",
        "Monster", "CareerBuilder", "Dice", "AngelList (Wellfound)",
        "Deel", "Remote.com", "Oyster HR", "Velocity Global",
    ],

    # ── Social Media Management ────────────────────────────────────────
    "Social Media Management": [
        "Hootsuite", "Buffer", "Sprout Social", "Later", "Loomly",
        "Agorapulse", "Sendible", "SocialBee", "Publer", "ContentStudio",
        "Planable", "CoSchedule", "MeetEdgar", "Tailwind", "Iconosquare",
        "Sociality.io", "Pallyy", "Vista Social", "Eclincher", "SocialPilot",
        "Falcon.io (Brandwatch)", "Khoros", "Sprinklr", "Emplifi",
        "Meltwater Social", "Talkwalker", "Brandwatch", "NetBase Quid",
        "Synthesio", "Digimind", "Keyhole", "Socialbakers (Emplifi)",
        "Dash Hudson", "Planoly", "Sked Social", "Combin",
        "Crowdfire", "Followerwonk", "SparkToro", "Audiense",
        "Shield (LinkedIn analytics)", "Inlytics", "AuthoredUp",
        "TubeBuddy", "vidIQ", "Social Blade", "NoxInfluencer",
        "CreatorIQ", "Grin", "Upfluence", "AspireIQ", "Traackr",
        "Influencity", "Heepsy", "Modash", "HypeAuditor", "Julius",
        "Klear", "Mavrck", "Impact.com", "PartnerStack",
        "Linktree", "Beacons", "Taplink", "Lnk.Bio", "Stan Store",
    ],

    # ── Email Marketing ────────────────────────────────────────────────
    "Email Marketing": [
        "Mailchimp", "Constant Contact", "ActiveCampaign", "ConvertKit",
        "MailerLite", "AWeber", "GetResponse", "Brevo (Sendinblue)",
        "Moosend", "Benchmark Email", "Campaign Monitor", "Emma",
        "Drip", "Klaviyo", "Omnisend", "Privy",
        "SendPulse", "Mailjet", "Sendy", "Listmonk",
        "Sender.net", "Flodesk", "Beehiiv", "Substack",
        "Ghost", "Buttondown", "Revue (Twitter)", "TinyLetter",
        "EmailOctopus", "Loops", "Resend", "Postmark",
        "SparkPost (MessageBird)", "Amazon SES", "Mandrill", "SendGrid",
        "Customer.io", "Vero", "Autopilot (Ortto)", "Userlist",
        "Encharge", "Drip", "Mailmodo", "Stripo",
        "BEE Pro", "Chamaileon", "Postcards (Designmodo)",
        "Litmus", "Email on Acid", "Mailtrap", "GlockApps",
        "ZeroBounce", "NeverBounce", "BriteVerify", "Kickbox",
        "Warmup Inbox", "Instantly Warmup", "Lemwarm", "Mailwarm",
    ],

    # ── Payment Processing ─────────────────────────────────────────────
    "Payment Processing": [
        "Stripe", "PayPal", "Square", "Adyen", "Braintree",
        "Worldpay", "Checkout.com", "Mollie", "Klarna", "Affirm",
        "Afterpay", "Sezzle", "Zip (Quadpay)", "Splitit",
        "Chargebee", "Recurly", "Zuora", "Paddle", "FastSpring",
        "2Checkout (Verifone)", "Razorpay", "Paystack", "Flutterwave",
        "dLocal", "Rapyd", "Nuvei", "Paysafe", "Payoneer",
        "Wise (TransferWise)", "Remitly", "WorldRemit", "Xoom",
        "Plaid", "Tink", "TrueLayer", "MX Technologies", "Yodlee",
        "Finicity", "Akoya", "Sopra Banking", "Temenos",
        "Marqeta", "Galileo", "i2c", "Lithic", "Privacy.com",
        "Synapse (Synapsepay)", "Bond", "Unit", "Treasury Prime",
        "GoCardless", "SlimPay", "TrustlyGroup", "Dwolla", "ACH.com",
        "Melio", "Bill.com", "Tipalti", "Trolley (Payment Rails)",
        "Hyperwallet (PayPal)", "Payability", "Behalf", "Fundbox",
        "BlueVine", "Kabbage (AmEx)", "OnDeck", "Lendio",
    ],

    # ── ERP Systems ────────────────────────────────────────────────────
    "ERP": [
        "SAP S/4HANA", "Oracle ERP Cloud", "Microsoft Dynamics 365",
        "NetSuite", "Sage Intacct", "Sage X3", "Sage 100",
        "Infor CloudSuite", "Epicor Kinetic", "IFS Cloud",
        "Acumatica", "Syspro", "Plex (Rockwell)", "QAD",
        "IQMS (DELMIAworks)", "Rootstock", "Cetec ERP", "Genius ERP",
        "Global Shop Solutions", "JobBOSS2", "E2 Shop System",
        "Odoo", "ERPNext", "Dolibarr", "Tryton", "Metasfresh",
        "Priority ERP", "UNIT4", "Workday Financials",
        "Brightpearl", "Cin7", "TradeGecko", "DEAR Inventory",
        "Katana MRP", "MRPeasy", "Fishbowl Manufacturing",
        "Arena Solutions (PTC)", "Propel", "OpenBOM",
        "SAP Business One", "SAP Business ByDesign",
        "Deltek", "Unanet", "BST Global", "Ajera",
        "Certinia (FinancialForce)", "Kimble", "Kantata",
        "Multiview", "MIP Fund Accounting", "Blackbaud Financial Edge",
    ],

    # ── Document Management ────────────────────────────────────────────
    "Document Management": [
        "DocuSign", "PandaDoc", "HelloSign", "Adobe Sign", "SignNow",
        "Dropbox", "Box", "Google Drive", "OneDrive", "SharePoint",
        "Notion", "Confluence", "Coda", "Slite", "Nuclino",
        "Tettra", "Guru", "Bloomfire", "Helpjuice", "Document360",
        "GitBook", "ReadMe", "Archbee", "Mintlify", "Docusaurus",
        "M-Files", "DocuWare", "Laserfiche", "Hyland OnBase",
        "OpenText", "Alfresco", "Nuxeo", "LogicalDOC", "Paperless-ngx",
        "Templafy", "Qorus", "Proposify", "Better Proposals", "Qwilr",
        "Canva Docs", "Beautiful.ai", "Pitch", "Tome", "Gamma",
        "Smallpdf", "PDF.co", "iLovePDF", "Nitro", "Foxit",
        "Adobe Acrobat", "PDFTron", "PSPDFKit", "Nutrient",
    ],

    # ── Customer Success ───────────────────────────────────────────────
    "Customer Success": [
        "Gainsight", "Totango", "ChurnZero", "ClientSuccess", "Planhat",
        "SmartKarrot", "Custify", "Akita", "Vitally", "Catalyst",
        "Strikedeck", "Kapta", "Amity", "Natero", "Bolstra",
        "UserIQ", "EverAfter", "Arrows", "OnRamp", "GUIDEcx",
        "Rocketlane", "Baton", "TaskRay", "Precursive",
        "UserVoice", "Canny", "ProductBoard", "Aha!", "Pendo",
        "Heap", "FullStory", "Hotjar", "Qualtrics XM",
        "Medallia", "InMoment", "Verint", "NICE Satmetrix",
        "Wootric", "Delighted", "AskNicely", "CustomerGauge",
        "Retently", "SurveySparrow", "Refiner", "Survicate",
        "Chargebee Retention", "Brightback", "ProsperStack", "Churnkey",
    ],

    # ── Product Management ─────────────────────────────────────────────
    "Product Management": [
        "Productboard", "Aha!", "Jira Product Discovery", "Linear",
        "Shortcut", "Height", "Notion (PM)", "Coda (PM)",
        "Airfocus", "ProdPad", "Craft.io", "Receptive", "Ducalis",
        "Fibery", "Hive", "Targetprocess", "Pivotal Tracker",
        "Pendo", "Amplitude", "Mixpanel", "Heap", "PostHog",
        "FullStory", "LogRocket", "Smartlook",
        "LaunchDarkly", "Split.io", "Unleash", "Flagsmith",
        "Maze", "UserTesting", "Lookback", "Hotjar Surveys",
        "UserZoom", "dscout", "Respondent", "UserInterviews",
        "Loom", "Miro", "FigJam", "Whimsical",
        "Productplan", "Roadmunk", "Dragonboat", "Gocious",
        "Harvestr", "Sleekplan", "Upvoty", "Frill", "Nolt",
        "Canny", "UserVoice", "Beamer", "LaunchNotes", "Released",
        "Changelogfy", "Announcekit", "Headway",
    ],

    # ── ABM / Intent Data ──────────────────────────────────────────────
    "ABM/Intent Data": [
        "6sense", "Demandbase", "Terminus", "RollWorks", "Triblio",
        "Madison Logic", "Bombora", "TechTarget Priority Engine",
        "G2 Buyer Intent", "Gartner Digital Markets",
        "DemandScience", "Anteriad (formerly Leadspace + True Influence)",
        "ZoomInfo Intent", "Clearbit Reveal", "Leadfeeder (Dealfront)",
        "Albacross", "Snitcher", "Lead Forensics", "VisitorQueue",
        "N.Rich", "Influ2", "Recotap", "Jabmo", "Kwanzoo",
        "PathFactory", "Uberflip", "LookBookHQ",
        "Folloze", "Turtl", "ON24", "Reachdesk", "Sendoso",
        "Postal.io", "Alyce", "PFL", "Printfection",
        "Drift", "Qualified", "Chili Piper", "RevenueHero",
        "Clearbit", "Enricher", "Datanyze", "BuiltWith",
    ],

    # ── Conversational AI / Chatbots ───────────────────────────────────
    "Conversational AI/Chatbots": [
        "Drift", "Intercom", "Qualified", "Tidio", "LiveChat",
        "Zendesk Chat", "Freshchat", "Crisp", "Olark", "Tawk.to",
        "Ada", "Forethought", "Thankful", "Ultimate.ai", "Cognigy",
        "Yellow.ai", "Haptik", "Kore.ai", "Amelia (IPsoft)",
        "Dialogflow (Google)", "Amazon Lex", "Azure Bot Service",
        "IBM Watson Assistant", "Rasa", "Botpress", "Landbot",
        "ManyChat", "Chatfuel", "MobileMonkey", "Customers.ai",
        "Botsify", "Aivo", "Inbenta", "Aisera", "Moveworks",
        "Rezolve.ai", "Espressive", "Leena AI", "Neocase",
        "Capacity", "Simpplr AI", "Gaspar.ai", "Workativ",
        "Voiceflow", "Botmock", "Botsociety", "BotStar",
        "Gupshup", "Sinch Engage", "Infobip", "Bird (MessageBird)",
        "LivePerson", "NICE CXone", "Genesys DX", "Sprinklr Service",
    ],

    # ── Content Management / CMS ───────────────────────────────────────
    "CMS": [
        "WordPress", "Drupal", "Joomla", "Wix", "Squarespace",
        "Webflow", "Ghost", "HubSpot CMS", "Contentful", "Sanity",
        "Strapi", "Prismic", "Storyblok", "Butter CMS", "Hygraph (GraphCMS)",
        "DatoCMS", "Agility CMS", "Kentico", "Kontent.ai",
        "Sitecore", "Adobe Experience Manager", "Optimizely",
        "Acquia (Drupal Cloud)", "Pantheon", "WP Engine",
        "Kinsta", "Flywheel", "Cloudways", "SiteGround",
        "Payload CMS", "KeystoneJS", "Directus", "Cockpit CMS",
        "Tina CMS", "Decap CMS (Netlify CMS)", "Forestry",
        "Builder.io", "Plasmic", "Makeswift", "Visual Editor (Stackbit)",
        "Unbounce", "Instapage", "Leadpages", "ClickFunnels", "Carrd",
        "Duda", "Weebly", "Jimdo", "GoDaddy Website Builder",
        "Zyro", "Shopify (CMS)", "BigCommerce (CMS)",
        "Craft CMS", "ExpressionEngine", "Textpattern", "Perch",
        "ProcessWire", "Grav", "Kirby", "Statamic",
    ],

    # ── Business Intelligence ──────────────────────────────────────────
    "Business Intelligence": [
        "Tableau", "Power BI", "Looker", "Qlik Sense", "Sisense",
        "Domo", "ThoughtSpot", "MicroStrategy", "Mode Analytics",
        "Sigma Computing", "GoodData", "Yellowfin BI", "Dundas BI",
        "Izenda", "Logi Analytics (Insight Software)", "Bold BI",
        "Zoho Analytics", "Google Data Studio (Looker Studio)",
        "Databox", "Klipfolio", "Geckoboard", "DashThis",
        "Cyfe", "Whatagraph", "Supermetrics",
        "Chartio", "Periscope Data (Sisense)", "Redash", "Metabase",
        "Apache Superset", "Lightdash", "Holistics", "Preset",
        "Toucan Toco", "Cumul.io", "Reveal", "Luzmo",
        "Count", "Hex", "Observable", "Deepnote", "Streamlit",
    ],

    # ── Expense Management ─────────────────────────────────────────────
    "Expense Management": [
        "Expensify", "SAP Concur", "Emburse (Certify + Abacus + Nexonia)",
        "Brex", "Ramp", "Divvy (Bill.com)", "Airbase",
        "Spendesk", "Pleo", "Moss", "Payhawk", "Soldo",
        "Center", "Fyle", "Zoho Expense", "Rydoo",
        "Navan (TripActions)", "TravelPerk", "Egencia", "CWT",
        "TripIt", "Lola.com", "Travelperk", "GetGoing",
    ],

    # ── Time Tracking ──────────────────────────────────────────────────
    "Time Tracking": [
        "Toggl Track", "Harvest", "Clockify", "RescueTime", "Hubstaff",
        "Time Doctor", "Timely", "DeskTime", "ActivTrak", "Teramind",
        "Veriato", "InterGuard", "WorkPuls", "CurrentWare",
        "TSheets (QuickBooks Time)", "Deputy", "When I Work", "Homebase",
        "ClockShark", "busybusy", "ExakTime", "Buddy Punch",
        "Jibble", "Calamari", "AttendanceBot", "Connecteam",
        "Paymo", "Everhour", "Tick", "Timecamp",
        "Mavenlink (Kantata)", "BigTime", "Accelo", "Scoro",
        "Replicon", "Journyx", "Pacific Timesheet",
    ],

    # ── Scheduling / Booking ───────────────────────────────────────────
    "Scheduling/Booking": [
        "Calendly", "Cal.com", "Acuity Scheduling", "YouCanBookMe",
        "SavvyCal", "Doodle", "Reclaim.ai", "Clockwise", "Motion",
        "SimplyBook.me", "Setmore", "Square Appointments", "Booksy",
        "Fresha", "Vagaro", "MindBody", "WellnessLiving",
        "Timely (booking)", "Phorest", "Rosy", "GlossGenius",
        "ServiceM8", "Housecall Pro", "Jobber", "ServiceTitan",
        "Picktime", "Appointy", "Zoho Bookings", "HoneyBook",
        "Dubsado", "17hats", "Studio Ninja", "Tave", "Sprout Studio",
        "OpenTable", "Resy", "Yelp Reservations", "SevenRooms",
        "Tock", "Toast", "Lightspeed Restaurant",
    ],

    # ── Survey / Feedback ──────────────────────────────────────────────
    "Survey/Feedback": [
        "SurveyMonkey", "Typeform", "Google Forms", "Qualtrics",
        "Jotform", "Tally", "Airtable Forms", "Cognito Forms",
        "Formstack", "Paperform", "SurveySparrow", "Alchemer",
        "Zoho Survey", "QuestionPro", "SoGoSurvey", "SmartSurvey",
        "Medallia", "InMoment", "Verint", "Confirmit (Forsta)",
        "Delighted", "AskNicely", "Wootric", "CustomerGauge",
        "Retently", "Refiner", "Survicate", "Usabilla (GetFeedback)",
        "UserVoice", "Canny", "Pendo Feedback", "Productboard",
        "Hotjar Surveys", "Qualaroo", "Ethnio", "Respondent",
        "UserTesting", "Lookback", "dscout", "UserZoom",
    ],

    # ── Compliance / GRC ───────────────────────────────────────────────
    "Compliance/GRC": [
        "Vanta", "Drata", "Secureframe", "Laika", "Sprinto",
        "Tugboat Logic", "Hyperproof", "AuditBoard", "Workiva",
        "LogicGate", "Diligent", "NAVEX Global", "SAI Global",
        "MetricStream", "ServiceNow GRC", "Riskonnect",
        "Archer (RSA)", "IBM OpenPages", "SAP GRC",
        "OneTrust", "TrustArc", "BigID", "Securiti.ai", "DataGrail",
        "Osano", "Ketch", "Transcend", "Segment (privacy)",
        "WireWheel", "Privacera", "Immuta", "Collibra (governance)",
        "Ethyca", "Mine PrivacyOps",
        "ComplyAdvantage", "Chainalysis", "Elliptic", "Featurespace",
        "Feedzai", "Sardine", "Unit21", "Alloy", "Hummingbird",
        "Onfido", "Jumio", "Veriff", "Persona", "Socure",
        "Sumsub", "Shufti Pro", "iDenfy", "Trulioo",
    ],

    # ── Proposal / Contract Management ─────────────────────────────────
    "Proposal/Contract Management": [
        "PandaDoc", "Proposify", "Qwilr", "Better Proposals",
        "GetAccept", "DealHub", "Clientpoint", "RFPIO (Responsive)",
        "Loopio", "Ombud", "RFP360", "QorusDocs",
        "Nusii", "Bidsketch", "QuoteWerks", "ConnectWise Sell",
        "Ignition (Practice Ignition)", "GoProposal", "Mimiran",
        "Ironclad", "Juro", "Agiloft", "ContractPodAi", "Icertis",
        "DocuSign CLM", "Evisort", "LinkSquares", "SpotDraft",
        "Precisely", "ContractWorks", "Concord", "Anapact",
        "Conga (Apttus)", "SpringCM", "Outlaw", "Summize",
    ],

    # ── Affiliate / Partner Management ─────────────────────────────────
    "Affiliate/Partner Management": [
        "Impact.com", "PartnerStack", "Partnerize", "Everflow",
        "Tune", "Post Affiliate Pro", "Refersion", "Tapfiliate",
        "LeadDyno", "ShareASale", "CJ Affiliate", "Rakuten Advertising",
        "Awin", "Pepperjam", "ClickBank", "Digistore24",
        "FirstPromoter", "Rewardful", "ReferralCandy", "Friendbuy",
        "Mention Me", "Extole", "Ambassador (Partnerize)", "Talkable",
        "Referral Rock", "InviteReferrals", "GrowSurf", "Viral Loops",
        "Impartner", "Allbound", "Zinfi", "Channeltivity",
        "Mindmatrix", "Magentrix", "PartnerPortal.io", "Kiflo",
        "Crossbeam", "Reveal (Crossbeam)", "Partnerbase",
        "WorkSpan", "Pronto", "Partner Fleet",
    ],

    # ── Event Management ───────────────────────────────────────────────
    "Event Management": [
        "Eventbrite", "Bizzabo", "Cvent", "Splash", "Whova",
        "Swapcard", "Hopin", "Airmeet", "Run The World", "Hubilo",
        "Goldcast", "ON24", "Welcome (Bizzabo)", "WorkCast",
        "BigMarker", "Attendease", "Grip", "Brella",
        "Accelevents", "PheedLoop", "EventMobi", "Socio (Webex Events)",
        "Circa", "vFairs", "6Connex", "Intrado (West)",
        "Monday Tickets", "Ticket Tailor", "Tito", "Luma",
        "Peatix", "Eventzilla", "TicketSpice", "Brown Paper Tickets",
        "Social Tables", "AllSeated (Prismm)", "EventDraw",
        "Tripleseat", "Gather", "Planning Pod", "Honeybook (events)",
        "Regpack", "Campsite Bio", "Bevy", "CMX Hub",
    ],

    # ── Property Management ────────────────────────────────────────────
    "Property Management": [
        "AppFolio", "Buildium", "Yardi Voyager", "RealPage",
        "Entrata", "ResMan", "Rent Manager", "MRI Software",
        "Propertyware", "TenantCloud", "Innago", "Avail",
        "Stessa", "DoorLoop", "RentRedi", "Hemlane",
        "Rentec Direct", "SimplifyEm", "Cozy (Apartments.com)",
        "TurboTenant", "Landlord Studio", "Rentrocket",
        "Guesty", "Hostaway", "Lodgify", "OwnerRez",
        "Hospitable (Smartbnb)", "Tokeet", "Avantio", "Cloudbeds",
        "Mews", "Hotelogix", "RoomRaccoon", "Little Hotelier",
        "ThinkReservations", "innRoad", "WebRezPro", "Hostfully",
        "Escapia (Vrbo)", "Streamline VRS", "Track (formerly TrackHS)",
        "BookingSync (Smily)", "365villas", "Lodgable",
    ],

    # ── Restaurant / Hospitality Tech ──────────────────────────────────
    "Restaurant/Hospitality Tech": [
        "Toast", "Square for Restaurants", "Lightspeed Restaurant",
        "TouchBistro", "Revel Systems", "Aloha (NCR)", "Oracle MICROS",
        "SpotOn", "Clover", "Upserve (Lightspeed)", "Lavu",
        "Cake (Sysco)", "Rezku", "GoTab", "Bbot",
        "MarketMan", "BlueCart", "Parsley", "Galley Solutions",
        "meez", "ChefTec", "CostGuard", "FoodCost Pro",
        "7shifts", "HotSchedules (Fourth)", "Homebase", "Sling",
        "Jolt", "Harri", "Workstream", "Poached Jobs",
        "OpenTable", "Resy", "Yelp Reservations", "SevenRooms",
        "Tock", "Wisely", "Eat App", "Yelp for Business",
        "Olo", "ChowNow", "DoorDash Storefront", "BentoBox",
        "Thanx", "Punchh", "LevelUp", "Paytronix",
        "Cloudbeds", "Mews", "StayNTouch", "Oracle Hospitality",
        "Amadeus (hospitality)", "Sabre Hospitality", "Agilysys",
    ],

    # ── Fitness / Wellness SaaS ────────────────────────────────────────
    "Fitness/Wellness": [
        "MindBody", "WellnessLiving", "Vagaro", "Fresha",
        "Glofox", "Wodify", "Pike13", "ZenPlanner",
        "ClubReady", "ABC Fitness (ABC Financial)", "Jonas Fitness",
        "GymMaster", "PerfectGym", "Virtuagym", "Gymdesk",
        "Exercise.com", "TrueCoach", "TrainHeroic", "TeamBuildr",
        "CoachAccountable", "PTminder", "My PT Hub", "Trainerize",
        "Everfit", "Nudge Coach", "Healthie", "Practice Better",
        "SimplePractice", "Jane App", "IntakeQ", "Owl Practice",
        "Therabill", "TheraPlatform", "TherapyAppointment",
        "ClassPass", "Gympass (Wellhub)", "Peerfit", "Burnalong",
        "Grokker", "Wellbeats", "Whil", "meQuilibrium",
    ],

    # ── Nonprofit / Fundraising ────────────────────────────────────────
    "Nonprofit/Fundraising": [
        "Blackbaud", "Bloomerang", "Kindful", "DonorPerfect", "Salsa Labs",
        "NeonCRM", "Little Green Light", "Network for Good",
        "Keela", "Virtuous", "Givebutter", "Zeffy", "Donorbox",
        "Classy", "GoFundMe Charity", "Mightycause", "OneCause",
        "GiveSmart", "Handbid", "BetterWorld", "SchoolAuction",
        "Qgiv", "MobileCause", "Snowball Fundraising",
        "Aplos", "Sumac", "CiviCRM", "Orange Theory",
        "Raiser's Edge (Blackbaud)", "Salesforce Nonprofit Cloud",
        "EveryAction (Bonterra)", "Luminate Online", "CharityEngine",
        "Double the Donation", "Matching Gift", "360MatchPro",
        "GrantHub", "Submittable", "Foundant", "SmartSimple",
        "Instrumentl", "Fluxx", "Benevity", "Bright Funds",
        "Percent", "Millie", "Deed", "WeHero",
    ],

    # ── Insurance Tech ─────────────────────────────────────────────────
    "Insurance Tech": [
        "Guidewire", "Duck Creek Technologies", "Majesco",
        "Sapiens", "EIS", "Insurity", "OneShield",
        "BriteCore", "Socotra", "Origami Risk", "Snapsheet",
        "Tractable", "Shift Technology", "Claim Genius",
        "Lemonade", "Root Insurance", "Metromile", "Hippo Insurance",
        "Next Insurance", "Pie Insurance", "Embroker", "Vouch",
        "Coalition", "At-Bay", "Corvus Insurance",
        "Bold Penguin", "Talage", "Tarmika", "Bindable",
        "AgentSync", "Canopy Connect", "Verisk", "LexisNexis Risk",
        "CCC Intelligent Solutions", "Mitchell", "Zywave", "Applied Epic",
        "HawkSoft", "EZLynx", "NowCerts", "AgencyZoom",
        "Vertafore", "Duck Creek", "Instec",
    ],

    # ── EdTech ─────────────────────────────────────────────────────────
    "EdTech": [
        "Coursera", "Udemy", "edX", "Skillshare", "MasterClass",
        "Khan Academy", "Duolingo", "Babbel", "Rosetta Stone", "Busuu",
        "Quizlet", "Chegg", "StudyBlue", "Brainly", "Photomath",
        "Byju's", "Unacademy", "Vedantu", "Toppr", "Doubtnut",
        "ClassDojo", "Seesaw", "Nearpod", "Pear Deck", "Kahoot!",
        "Quizizz", "Socrative", "Mentimeter", "Poll Everywhere",
        "Prezi", "Google Classroom", "Schoology", "Canvas",
        "PowerSchool", "Infinite Campus", "Tyler SIS", "Blackbaud (K-12)",
        "Alma SIS", "Gradelink", "Veracross",
        "Instructure", "D2L Brightspace", "Blackboard", "Moodle",
        "Turnitin", "Grammarly (edu)", "ProctorU", "Examity",
        "Honorlock", "Proctorio", "Respondus",
        "Labster", "PhET", "Explorelearning", "Phet Interactive Simulations",
        "Newsela", "CommonLit", "IXL", "DreamBox", "ST Math",
    ],

    # ── AgTech ─────────────────────────────────────────────────────────
    "AgTech": [
        "John Deere Operations Center", "Climate FieldView",
        "Trimble Ag", "AGCO Fuse", "CNH Industrial",
        "Granular", "FarmLogs", "Bushel", "Conservis",
        "AgWorld", "Cropio", "OneSoil", "Sentera",
        "Taranis", "Prospera (Valmont)", "CropX", "Arable",
        "Farmers Edge", "Precision Planting", "AgVend",
        "Proagrica", "DTN", "Gro Intelligence", "Indigo Ag",
        "Pivot Bio", "Sound Agriculture", "Arva Intelligence",
        "FarmRaise", "Tillable", "Harvest Profit", "AgriWebb",
        "Datamars", "Allflex", "Cainthus", "Connecterra",
        "FarmBot", "Iron Ox", "AppHarvest", "Bowery Farming",
        "Plenty", "AeroFarms",
    ],

    # ── FinTech / Banking SaaS ─────────────────────────────────────────
    "FinTech/Banking": [
        "Stripe", "Square", "PayPal", "Adyen", "Braintree",
        "Plaid", "MX Technologies", "Yodlee", "Finicity", "Tink",
        "TrueLayer", "Akoya", "Sopra Banking", "Temenos",
        "FIS", "Fiserv", "Jack Henry", "Finastra",
        "nCino", "Blend", "Roostify", "Encompass (ICE Mortgage)",
        "Black Knight", "Ellie Mae",
        "Marqeta", "Galileo", "i2c", "Lithic", "Privacy.com",
        "Synapse", "Bond", "Unit", "Treasury Prime",
        "Robinhood", "Wealthfront", "Betterment", "Acorns",
        "Stash", "Public.com", "M1 Finance", "SoFi",
        "Chime", "Current", "Varo", "Dave", "MoneyLion",
        "Step", "Greenlight", "GoHenry",
        "Codat", "Rutter", "Railz", "Heron Data", "Canopy Servicing",
        "LoanPro", "TurnKey Lender", "Mambu", "Thought Machine",
        "10x Banking", "Zafin", "Backbase", "Q2",
        "Plaid", "Visa Developer", "Mastercard APIs",
        "Dwolla", "Astra", "Moov Financial", "Modern Treasury",
        "Column", "SVB APIs", "Cross River", "Synapse Financial",
    ],

    # ── Bonus: AI/ML Platforms ─────────────────────────────────────────
    "AI/ML Platforms": [
        "OpenAI", "Anthropic", "Google DeepMind", "Cohere", "AI21 Labs",
        "Hugging Face", "Replicate", "Anyscale", "Weights & Biases",
        "Neptune.ai", "Comet ML", "MLflow", "DataRobot", "H2O.ai",
        "Dataiku", "RapidMiner", "KNIME", "Alteryx",
        "Scale AI", "Labelbox", "V7", "SuperAnnotate", "Snorkel AI",
        "Jasper", "Copy.ai", "Writer", "Writesonic",
        "Grammarly", "ProWritingAid", "Hemingway Editor",
        "Midjourney", "Stability AI", "RunwayML", "Pika",
        "ElevenLabs", "Play.ht", "LOVO", "Murf.ai", "Resemble AI",
        "Speechify", "WellSaid Labs", "Replica Studios",
        "Perplexity AI", "You.com", "Phind", "Kagi",
        "GitHub Copilot", "Tabnine", "Codeium", "Replit AI",
        "Cursor", "Vercel v0", "Bolt.new", "Lovable",
        "Pinecone", "Weaviate", "Qdrant", "ChromaDB", "Zilliz",
        "LangChain", "LlamaIndex", "Haystack",
    ],

    # ── Bonus: Workflow Automation ─────────────────────────────────────
    "Workflow Automation": [
        "Zapier", "Make (Integromat)", "n8n", "Tray.io", "Workato",
        "Power Automate", "IFTTT", "Pipedream", "Parabola", "Bardeen",
        "Relay.app", "Integrately", "LeadsBridge", "Automate.io",
        "Pabbly Connect", "KonnectzIT", "SyncSpider", "Celigo",
        "Boomi", "MuleSoft", "SnapLogic", "Jitterbit",
        "Talend", "Informatica", "Fivetran", "Airbyte",
        "Hevo Data", "Stitch", "Rivery", "Hightouch",
        "Census", "Rudderstack", "Lytics",
        "Monday Automations", "ClickUp Automations", "Asana Rules",
        "Notion Automations", "Airtable Automations",
    ],

    # ── Bonus: Procurement / Sourcing ──────────────────────────────────
    "Procurement/Sourcing": [
        "Coupa", "SAP Ariba", "JAGGAER", "GEP SMART", "Ivalua",
        "Zycus", "Procurify", "Precoro", "SpendHQ", "Sievo",
        "Simfoni", "Fairmarkit", "Raiven", "Globality",
        "Scout RFP (WorkDay)", "Bonfire", "ProcurePort",
        "Vendavo", "PROS", "Zilliant", "Pricefx",
        "Competera", "Intelligence Node", "Prisync",
    ],

    # ── Bonus: CPQ (Configure-Price-Quote) ─────────────────────────────
    "CPQ": [
        "Salesforce CPQ", "DealHub CPQ", "Conga CPQ", "PROS CPQ",
        "Oracle CPQ", "SAP CPQ", "Vendavo", "ConnectWise CPQ",
        "PandaDoc CPQ", "Proposify", "QuoteWerks",
        "Cincom", "Epicor CPQ", "KBMax (Epicor)", "DriveWorks",
    ],

    # ── Bonus: Localization / Translation ──────────────────────────────
    "Localization/Translation": [
        "Smartling", "Phrase (Memsource)", "Lokalise", "Crowdin",
        "Transifex", "POEditor", "Weglot", "Bablic", "Localize",
        "Smartcat", "memoQ", "SDL Trados", "XTM Cloud",
        "Lilt", "Unbabel", "DeepL", "Google Translate API",
        "Amazon Translate", "Azure Translator",
    ],

    # ── Bonus: iPaaS / API Management ──────────────────────────────────
    "iPaaS/API": [
        "MuleSoft", "Boomi", "Workato", "Tray.io", "Celigo",
        "SnapLogic", "Jitterbit", "Microsoft Azure Integration Services",
        "AWS API Gateway", "Kong", "Apigee", "Postman",
        "RapidAPI", "Gravitee", "Tyk", "WSO2",
        "SwaggerHub", "Stoplight", "ReadMe", "Redocly",
    ],
}


def main():
    # Start with existing names from previously collected data
    all_names = load_existing()
    print(f"Loaded {len(all_names)} names from existing data files.")

    # Add all curated names
    added = 0
    for category, names in COMPANIES_BY_CATEGORY.items():
        for name in names:
            clean = name.strip()
            if clean:
                all_names.add(clean)
                added += 1

    # Deduplicate case-insensitively: keep the first-seen casing
    seen_lower = {}
    for name in sorted(all_names):
        key = name.lower()
        if key not in seen_lower:
            seen_lower[key] = name

    unique_names = sorted(seen_lower.values(), key=str.lower)

    print(f"Added {added} curated names across {len(COMPANIES_BY_CATEGORY)} categories.")
    print(f"Total unique companies (case-insensitive dedup): {len(unique_names)}")

    # Save
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(unique_names, f, indent=2)

    print(f"Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
