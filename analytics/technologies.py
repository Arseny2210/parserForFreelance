from typing import Optional
import re
from collections import Counter

TECHNOLOGY_PATTERNS: dict[str, list[str]] = {
    "Python": [r"\bpython\b", r"\bpython3\b", r"\bpython2\b"],
    "JavaScript": [r"\bjavascript\b", r"\bjs\b(?!\.)", r"\bes6\b", r"\bnode\.?js\b"],
    "TypeScript": [r"\btypescript\b", r"\bts\b(?!\.)", r"\b\.tsx?\b"],
    "React": [r"\breact\b", r"\breactjs\b", r"\bjsx\b", r"\btsx\b"],
    "React Native": [r"\breact\s*native\b", r"\breactnative\b"],
    "Vue.js": [r"\bvue\b", r"\bvue\.?js\b", r"\bvue3\b", r"\bnuxt\b"],
    "Angular": [r"\bangular\b", r"\bangulr\b", r"\brxjs\b"],
    "Svelte": [r"\bsvelte\b", r"\bsveltekit\b"],
    "Next.js": [r"\bnext\.?js\b", r"\bnextjs\b"],
    "Node.js": [r"\bnode\b", r"\bnode\.?js\b", r"\bnpm\b", r"\byarn\b"],
    "Django": [r"\bdjango\b", r"\bdrf\b", r"\bdjango-rest\b"],
    "Flask": [r"\bflask\b"],
    "FastAPI": [r"\bfastapi\b", r"\bfastapi\b"],
    "Laravel": [r"\blaravel\b"],
    "PHP": [r"\bphp\b"],
    "Ruby": [r"\bruby\b", r"\brails\b", r"\bruby\s*on\s*rails\b"],
    "Java": [r"\bjava\b", r"\bspring\s*boot\b", r"\bspring\b"],
    "Kotlin": [r"\bkotlin\b"],
    "Swift": [r"\bswift\b", r"\bswiftui\b"],
    "C#": [r"\bc#\b", r"\bcsharp\b", r"\b\.net\b", r"\basp\.net\b", r"\bdotnet\b"],
    "Go": [
        r"\bgolang\b",
        r"\bgo\s*language\b",
        r"\bgo\b(?!\.)(?:\s+program|\s+dev|\s+api)",
    ],
    "Rust": [r"\brust\b"],
    "SQL": [
        r"\bsql\b",
        r"\bpostgresql\b",
        r"\bpostgres\b",
        r"\bmysql\b",
        r"\bmariadb\b",
        r"\bsqlite\b",
    ],
    "MongoDB": [r"\bmongodb\b", r"\bmongo\b", r"\bmongoose\b"],
    "Redis": [r"\bredis\b"],
    "Docker": [r"\bdocker\b", r"\bdockerfile\b", r"\bdocker-compose\b"],
    "Kubernetes": [r"\bkubernetes\b", r"\bk8s\b", r"\bkube\b"],
    "AWS": [
        r"\baws\b",
        r"\bamazon\s*web\s*services\b",
        r"\bec2\b",
        r"\bs3\b",
        r"\blambda\b",
    ],
    "GCP": [r"\bgcp\b", r"\bgoogle\s*cloud\b", r"\bgcloud\b"],
    "Azure": [r"\bazure\b", r"\bms\s*azure\b"],
    "Git": [r"\bgit\b", r"\bgithub\b", r"\bgitlab\b", r"\bbitbucket\b"],
    "Docker Compose": [r"\bdocker.compose\b"],
    "Nginx": [r"\bnginx\b"],
    "GraphQL": [r"\bgraphql\b", r"\bapollo\b"],
    "REST": [r"\brest\s*api\b", r"\brestful\b"],
    "WebSocket": [r"\bwebsocket\b", r"\bsocket\.io\b", r"\bws\b"],
    "Selenium": [r"\bselenium\b"],
    "Playwright": [r"\bplaywright\b"],
    "TensorFlow": [r"\btensorflow\b", r"\btf\b"],
    "PyTorch": [r"\bpytorch\b"],
    "Scikit-learn": [r"\bscikit.learn\b", r"\bsklearn\b"],
    "Pandas": [r"\bpandas\b"],
    "NumPy": [r"\bnumpy\b"],
    "OpenCV": [r"\bopencv\b"],
    "PostgreSQL": [r"\bpostgresql\b", r"\bpostgres\b"],
    "MySQL": [r"\bmysql\b"],
    "SQLite": [r"\bsqlite\b"],
    "Redis": [r"\bredis\b"],
    "Elasticsearch": [r"\belasticsearch\b", r"\belastic\b"],
    "RabbitMQ": [r"\brabbitmq\b"],
    "Kafka": [r"\bkafka\b"],
    "Celery": [r"\bcelery\b"],
    "WordPress": [r"\bwordpress\b", r"\bwp\b"],
    "Shopify": [r"\bshopify\b"],
    "WooCommerce": [r"\bwoocommerce\b", r"\bwoo\b"],
    "Figma": [r"\bfigma\b"],
    "Tailwind": [r"\btailwind\b", r"\btailwindcss\b"],
    "Bootstrap": [r"\bbootstrap\b"],
    "jQuery": [r"\bjquery\b"],
    "Three.js": [r"\bthree\.?js\b"],
    "D3.js": [r"\bd3\.?js\b", r"\bd3\b"],
    "Chart.js": [r"\bchart\.?js\b"],
    "Cypress": [r"\bcypress\b"],
    "Jest": [r"\bjest\b"],
    "Pytest": [r"\bpytest\b"],
    "LangChain": [r"\blangchain\b"],
    "LlamaIndex": [r"\bllamaindex\b"],
    "Hugging Face": [r"\bhugging\s*face\b", r"\bhuggingface\b", r"\btransformers?\b"],
    "OpenAI": [r"\bopenai\b", r"\bgpt\b", r"\bchatgpt\b"],
    "Claude": [r"\bclaude\b", r"\banthropic\b"],
    "n8n": [r"\bn8n\b"],
    "Make": [r"\bmake\.com\b", r"\bintegromat\b"],
    "Zapier": [r"\bzapier\b"],
    "Flutter": [r"\bflutter\b", r"\bdart\b"],
    "Unity": [r"\bunity\b"],
    "Unreal Engine": [r"\bunreal\s*engine\b", r"\bunreal\b"],
    "Terraform": [r"\bterraform\b"],
    "Ansible": [r"\bansible\b"],
    "Prometheus": [r"\bprometheus\b"],
    "Grafana": [r"\bgrafana\b"],
    "Power BI": [r"\bpower\s*bi\b", r"\bpowerbi\b"],
    "Tableau": [r"\btableau\b"],
}

TECH_STACK_MAP: dict[str, list[str]] = {
    "Python": ["Backend", "Machine Learning", "Data Analytics", "Automation"],
    "JavaScript": ["Frontend", "Backend", "Fullstack"],
    "TypeScript": ["Frontend", "Backend", "Fullstack"],
    "React": ["Frontend", "Fullstack"],
    "Next.js": ["Frontend", "Fullstack"],
    "Vue.js": ["Frontend"],
    "Angular": ["Frontend"],
    "Django": ["Backend", "Fullstack"],
    "Flask": ["Backend"],
    "FastAPI": ["Backend"],
    "Laravel": ["Backend", "Fullstack"],
    "Node.js": ["Backend", "Fullstack"],
    "Docker": ["DevOps"],
    "Kubernetes": ["DevOps"],
    "PostgreSQL": ["Backend", "Data Analytics"],
    "OpenAI": ["AI Chatbots", "AI Agents", "RAG", "OpenAI Integration"],
    "LangChain": ["RAG", "AI Agents", "LLM"],
    "Flutter": ["Mobile Apps", "Flutter"],
    "WordPress": ["WordPress"],
    "Shopify": ["Shopify"],
    "Selenium": ["Web Scraping", "QA"],
    "Playwright": ["Web Scraping", "QA"],
    "TensorFlow": ["Machine Learning", "Computer Vision"],
    "PyTorch": ["Machine Learning", "Computer Vision"],
}


class TechnologyExtractor:
    def __init__(self) -> None:
        self.patterns = TECHNOLOGY_PATTERNS

    def extract(
        self,
        title: str,
        description: Optional[str] = None,
        existing_technologies: Optional[list[str]] = None,
    ) -> list[str]:
        text = (title + " " + (description or "")).lower()
        found: set[str] = set()

        if existing_technologies:
            for tech in existing_technologies:
                tech_lower = tech.lower().strip()
                found.add(tech_lower)

        for tech_name, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    found.add(tech_name)
                    break

        return sorted(found)

    def get_technology_frequencies(self, tasks: list[dict]) -> dict[str, int]:
        counter: Counter = Counter()
        for task in tasks:
            technologies = task.get("technologies", [])
            if isinstance(technologies, list):
                for tech in technologies:
                    if isinstance(tech, str):
                        counter[tech] += 1
        return dict(counter.most_common())


extractor = TechnologyExtractor()
