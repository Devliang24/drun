import { useMemo, useState } from 'react';
import {
  ArrowRight,
  BookOpen,
  Check,
  Clipboard,
  ExternalLink,
  Menu,
  X,
} from 'lucide-react';
import {
  cliOutput,
  diagnostics,
  docs,
  featureCards,
  heroYaml,
  navItems,
  tutorials,
  type CodeSample,
} from './content';

function CodeBlock({ sample, compact = false }: { sample: CodeSample; compact?: boolean }) {
  const [copied, setCopied] = useState(false);

  async function copyCode() {
    try {
      await navigator.clipboard.writeText(sample.code);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1400);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className={`code-block ${compact ? 'compact' : ''}`}>
      <div className="code-toolbar">
        <span>{sample.language}</span>
        <button type="button" className="icon-button" onClick={copyCode} aria-label="复制代码">
          {copied ? <Check size={16} /> : <Clipboard size={16} />}
        </button>
      </div>
      <pre>
        <code>{sample.code}</code>
      </pre>
    </div>
  );
}

function Header() {
  const [open, setOpen] = useState(false);

  return (
    <header className="topbar">
      <a className="brand" href="#home" aria-label="Drun 首页">
        <span className="brand-mark">D</span>
        <span>Drun</span>
      </a>

      <nav className="desktop-nav" aria-label="主导航">
        {navItems.map((item) => (
          <a key={item.id} href={`#${item.id}`}>
            {item.label}
          </a>
        ))}
        <a href="https://github.com/Devliang24/drun" target="_blank" rel="noreferrer">
          GitHub
        </a>
      </nav>

      <button className="mobile-menu" type="button" onClick={() => setOpen((value) => !value)} aria-label="打开导航">
        {open ? <X size={22} /> : <Menu size={22} />}
      </button>

      {open ? (
        <nav className="mobile-nav" aria-label="移动导航">
          {navItems.map((item) => (
            <a key={item.id} href={`#${item.id}`} onClick={() => setOpen(false)}>
              {item.label}
            </a>
          ))}
          <a href="https://github.com/Devliang24/drun" target="_blank" rel="noreferrer" onClick={() => setOpen(false)}>
            GitHub
          </a>
        </nav>
      ) : null}
    </header>
  );
}

function Hero() {
  return (
    <section className="hero section" id="home">
      <div className="hero-copy">
        <p className="eyebrow">YAML 驱动的 HTTP API 测试框架</p>
        <h1>Drun</h1>
        <p className="lead">
          用简洁 YAML 描述请求、变量提取、断言、套件编排和报告输出，把接口验证、调试与 CI/CD 串成一条可维护链路。
        </p>
        <div className="hero-actions">
          <a className="primary-button" href="#docs">
            <BookOpen size={18} />
            阅读文档
          </a>
          <a className="secondary-button" href="https://github.com/Devliang24/drun" target="_blank" rel="noreferrer">
            <ExternalLink size={18} />
            GitHub
          </a>
        </div>
        <div className="install-line" aria-label="安装命令">
          <code>pip install drun</code>
        </div>
      </div>

      <div className="product-stage" aria-label="Drun 产品预览">
        <div className="preview-column wide">
          <div className="panel-title">testcases/test_user_api.yaml</div>
          <CodeBlock sample={{ language: 'yaml', code: heroYaml }} compact />
        </div>
        <div className="preview-column">
          <div className="panel-title">CLI</div>
          <CodeBlock sample={{ language: 'text', code: cliOutput }} compact />
          <div className="report-card">
            <div className="report-header">
              <span>HTML Report</span>
              <span className="status-dot">passed</span>
            </div>
            <div className="report-grid">
              <span>Cases</span>
              <strong>6 / 6</strong>
              <span>Steps</span>
              <strong>18 / 18</strong>
              <span>Pass Rate</span>
              <strong>100%</strong>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function FeatureGrid() {
  return (
    <section className="section feature-section" aria-labelledby="feature-title">
      <div className="section-heading">
        <p className="eyebrow">核心能力</p>
        <h2 id="feature-title">为 API 测试链路设计的工作台</h2>
      </div>
      <div className="feature-grid">
        {featureCards.map((feature) => {
          const Icon = feature.icon;
          return (
            <article className="feature-card" key={feature.title}>
              <Icon size={22} />
              <h3>{feature.title}</h3>
              <p>{feature.text}</p>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function DocsSection() {
  const [activeId, setActiveId] = useState(docs[0].id);
  const activeDoc = useMemo(() => docs.find((doc) => doc.id === activeId) ?? docs[0], [activeId]);
  const Icon = activeDoc.icon;

  return (
    <section className="section docs-section" id="docs" aria-labelledby="docs-title">
      <div className="section-heading">
        <p className="eyebrow">文档</p>
        <h2 id="docs-title">从快速开始到深度用法</h2>
      </div>
      <div className="docs-layout">
        <div className="doc-tabs" role="tablist" aria-label="文档主题">
          {docs.map((doc) => {
            const TabIcon = doc.icon;
            return (
              <button
                key={doc.id}
                type="button"
                className={doc.id === activeId ? 'active' : ''}
                onClick={() => setActiveId(doc.id)}
                role="tab"
                aria-selected={doc.id === activeId}
              >
                <TabIcon size={18} />
                <span>{doc.title}</span>
              </button>
            );
          })}
        </div>
        <article className="doc-detail">
          <div className="doc-detail-head">
            <Icon size={28} />
            <div>
              <p className="eyebrow">{activeDoc.kicker}</p>
              <h3>{activeDoc.title}</h3>
            </div>
          </div>
          <p>{activeDoc.summary}</p>
          <ul>
            {activeDoc.bullets.map((bullet) => (
              <li key={bullet}>{bullet}</li>
            ))}
          </ul>
          <CodeBlock sample={activeDoc.sample} />
        </article>
      </div>
    </section>
  );
}

function TutorialsSection() {
  return (
    <section className="section tutorials-section" id="tutorials" aria-labelledby="tutorials-title">
      <div className="section-heading">
        <p className="eyebrow">教程博客</p>
        <h2 id="tutorials-title">按真实工作流学习 Drun</h2>
      </div>
      <div className="tutorial-grid">
        {tutorials.map((tutorial) => (
          <article className="tutorial-card" key={tutorial.id}>
            <h3>{tutorial.title}</h3>
            <p>{tutorial.summary}</p>
            <ol>
              {tutorial.steps.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
            <CodeBlock sample={tutorial.sample} compact />
          </article>
        ))}
      </div>
    </section>
  );
}

function TroubleshootingSection() {
  return (
    <section className="section troubleshooting-section" id="troubleshooting" aria-labelledby="troubleshooting-title">
      <div className="section-heading">
        <p className="eyebrow">排障</p>
        <h2 id="troubleshooting-title">稳定错误码，直接给修复方向</h2>
      </div>
      <div className="diagnostic-layout">
        <div className="diagnostic-table" role="table" aria-label="Drun YAML 诊断错误码">
          {diagnostics.map(([code, title, hint]) => (
            <div className="diagnostic-row" role="row" key={code}>
              <code>{code}</code>
              <strong>{title}</strong>
              <span>{hint}</span>
            </div>
          ))}
        </div>
        <div className="diagnostic-example">
          <CodeBlock
            sample={{
              language: 'text',
              code: `DRUN-YAML-003 Invalid request field: request.url
File: testcases/test_demo.yaml:8
Path: steps[0].request.url

Use request.path instead of request.url.

Example:
  request:
    method: GET
    path: /api/users`,
            }}
          />
        </div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="footer">
      <div>
        <strong>Drun</strong>
        <p>现代 HTTP API 测试框架。</p>
      </div>
      <div className="footer-links">
        <a href="https://github.com/Devliang24/drun" target="_blank" rel="noreferrer">
          GitHub <ExternalLink size={14} />
        </a>
        <a href="https://github.com/Devliang24/drun/blob/main/README.en.md" target="_blank" rel="noreferrer">
          English README <ExternalLink size={14} />
        </a>
      </div>
    </footer>
  );
}

export function App() {
  return (
    <div className="app-shell">
      <Header />
      <main>
        <Hero />
        <FeatureGrid />
        <DocsSection />
        <TutorialsSection />
        <TroubleshootingSection />
        <section className="section cta-band" aria-label="开始使用 Drun">
          <div>
            <p className="eyebrow">开始使用</p>
            <h2>先写一个 Case，再让 drun check 帮你守住 DSL 质量。</h2>
          </div>
          <a className="primary-button" href="#docs">
            进入快速开始
            <ArrowRight size={18} />
          </a>
        </section>
      </main>
      <Footer />
    </div>
  );
}
