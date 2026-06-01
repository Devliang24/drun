import { useEffect, useMemo, useState } from 'react';
import {
  ArrowRight,
  BookOpen,
  Check,
  CheckCircle2,
  Clipboard,
  Code2,
  ExternalLink,
  FileJson2,
  GitBranch,
  Menu,
  PlayCircle,
  Repeat2,
  ServerCog,
  Terminal,
  Wrench,
  X,
} from 'lucide-react';
import {
  agentSkillContent,
  docGroups,
  docPages,
  findPage,
  homeCli,
  homeYaml,
  pageById,
  type ArticlePage as ArticlePageType,
  type ArticleSection,
  type CodeSample,
} from './content';

const legacyRouteRedirects: Record<string, string> = {
  '/docs/assertions-extract': '/docs/checks-extract',
  '/tutorials/first-case': '/docs/getting-started',
  '/tutorials/login-flow': '/docs/composition',
  '/tutorials/check-diagnostics': '/docs/troubleshooting',
  '/tutorials/curl-openapi': '/docs/debug-migration',
};

function routeFromHash() {
  const raw = window.location.hash.replace(/^#/, '');
  if (!raw || raw === '/') {
    return '/';
  }
  const route = raw.startsWith('/') ? raw : `/${raw}`;
  return legacyRouteRedirects[route] ?? route;
}

function rawRouteFromHash() {
  const raw = window.location.hash.replace(/^#/, '');
  if (!raw || raw === '/') {
    return '/';
  }
  return raw.startsWith('/') ? raw : `/${raw}`;
}

function href(path: string) {
  return `#${path}`;
}

function CodeBlock({ sample, compact = false, wrap = false }: { sample: CodeSample; compact?: boolean; wrap?: boolean }) {
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
    <div className={`code-block ${compact ? 'compact' : ''} ${wrap ? 'wrap' : ''}`}>
      <div className="code-toolbar">
        <span>{sample.title ?? sample.language}</span>
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

function Header({ route }: { route: string }) {
  const [open, setOpen] = useState(false);
  const nav = [
    { label: '首页', path: '/' },
    { label: '文档', path: '/docs/getting-started' },
    { label: '排障', path: '/docs/troubleshooting' },
    { label: 'Agent Skill', path: '/agent-skill' },
  ];
  const isNavActive = (path: string) => {
    if (path === '/') {
      return route === '/';
    }
    if (path === '/docs/troubleshooting') {
      return route === path;
    }
    if (path.startsWith('/docs')) {
      return route.startsWith('/docs') && route !== '/docs/troubleshooting';
    }
    return route === path;
  };

  return (
    <header className="topbar">
      <a className="brand" href={href('/')} aria-label="Drun 首页" onClick={() => setOpen(false)}>
        <span className="brand-mark">D</span>
        <span>Drun</span>
      </a>

      <nav className="desktop-nav" aria-label="主导航">
        {nav.map((item) => (
          <a key={item.path} className={isNavActive(item.path) ? 'active' : ''} href={href(item.path)}>
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
          {nav.map((item) => (
            <a key={item.path} href={href(item.path)} onClick={() => setOpen(false)}>
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

function HomePage() {
  const productPillars = [
    {
      icon: Code2,
      title: '把接口请求写成可维护资产',
      text: '用 YAML 描述 method、path、headers、body、extract 和 check，测试内容不再散落在临时脚本和调试记录里。',
    },
    {
      icon: GitBranch,
      title: '把真实业务链路串起来',
      text: '用 invoke、caseflow、repeat、sleep 组合登录后链路、异步轮询和跨 Case 复用，适合团队沉淀冒烟与回归场景。',
    },
    {
      icon: CheckCircle2,
      title: '先发现作者错误再执行请求',
      text: 'drun c 聚合 YAML 诊断，输出稳定错误码、文件位置、Path、hint 和短示例，把常见写法错误提前拦住。',
    },
    {
      icon: FileJson2,
      title: '让结果能复现、能归档',
      text: '运行后输出 HTML、JSON、Allure、snippet 和响应体保存结果，失败请求可以快速复现，也能接入 CI 归档。',
    },
  ];

  const workflow = [
    {
      step: '01',
      title: '写 Case',
      text: '从一个接口开始，把请求、提取和检查写进 YAML。',
      icon: Code2,
    },
    {
      step: '02',
      title: '检查 DSL',
      text: '用 drun c 批量发现字段写错、参数位置错误和无效组合。',
      icon: CheckCircle2,
    },
    {
      step: '03',
      title: '按环境运行',
      text: '通过 -env 和 -vars 切换环境与变量，单文件调试后再批量跑目录。',
      icon: PlayCircle,
    },
    {
      step: '04',
      title: '交付报告',
      text: '输出报告、snippet 和保存文件，让失败复现和团队协作更轻。',
      icon: FileJson2,
    },
  ];

  const capabilities = [
    { icon: Terminal, title: '请求建模', text: 'method、path、headers、body、data、files、auth、stream' },
    { icon: Repeat2, title: '数据驱动', text: 'config.parameters、CSV、product、zip' },
    { icon: GitBranch, title: '链路编排', text: 'caseflow、invoke、invoke_case_name(s)、repeat、sleep' },
    { icon: ServerCog, title: '环境运行', text: 'drun r、drun c、-env、-vars、-failfast、-persist-env' },
    { icon: FileJson2, title: '报告输出', text: 'HTML、JSON、Allure、curl snippet、保存响应体、CSV 导出' },
    { icon: Wrench, title: '调试迁移', text: 'drun q、cURL / HAR / Postman / OpenAPI 转 YAML、export curl' },
  ];

  return (
    <main>
      <section className="product-hero">
        <div className="hero-backdrop" aria-hidden="true">
          <div className="backdrop-panel">
            <span>$ drun c tcases</span>
            <strong>Checked 8 file(s): 8 OK</strong>
          </div>
          <div className="backdrop-panel accent">
            <span>DRUN-YAML-003</span>
            <strong>Use request.path instead of request.url</strong>
          </div>
          <div className="backdrop-panel">
            <span>HTML Report</span>
            <strong>Cases 6 / 6 · Pass Rate 100%</strong>
          </div>
        </div>
        <div className="product-hero-inner">
          <div className="hero-product-copy">
            <p className="eyebrow">YAML-driven HTTP API testing</p>
            <h1>Drun</h1>
            <p className="product-lead">
              用 YAML 把接口调试、链路测试、环境变量、诊断排障和报告输出沉淀成团队可维护的测试资产。
            </p>
            <div className="hero-command" aria-label="快速开始命令">
              <span>$</span>
              <code>pip install drun && drun i api-tests</code>
            </div>
            <div className="hero-actions">
              <a className="primary-button" href={href('/docs/getting-started')}>
                <BookOpen size={18} />
                快速开始
              </a>
              <a className="secondary-button" href={href('/docs/yaml-dsl')}>
                <Code2 size={18} />
                查看 DSL
              </a>
              <a className="secondary-button" href="https://github.com/Devliang24/drun" target="_blank" rel="noreferrer">
                <ExternalLink size={18} />
                GitHub
              </a>
            </div>
          </div>

          <div className="hero-proof" aria-label="Drun 核心价值">
            <div>
              <strong>YAML DSL</strong>
              <span>请求、变量、检查</span>
            </div>
            <div>
              <strong>drun c</strong>
              <span>稳定错误码与修复建议</span>
            </div>
            <div>
              <strong>caseflow</strong>
              <span>组合登录后业务链路</span>
            </div>
            <div>
              <strong>Reports</strong>
              <span>HTML / JSON / Allure / snippet</span>
            </div>
          </div>
        </div>
      </section>

      <section className="product-section product-showcase">
        <div className="section-heading split-heading">
          <div>
            <p className="eyebrow">产品形态</p>
            <h2>一个 Case，一次检查，一份可分享报告</h2>
          </div>
          <a className="text-link" href={href('/docs/getting-started')}>
            跟着写第一个 Case <ArrowRight size={16} />
          </a>
        </div>
        <div className="product-demo" aria-label="Drun 产品预览">
          <div className="demo-pane demo-yaml">
            <div className="panel-title">tcases/tc_user_api.yaml</div>
            <CodeBlock sample={{ language: 'yaml', code: homeYaml }} compact />
          </div>
          <div className="demo-pane">
            <div className="panel-title">CLI</div>
            <CodeBlock sample={{ language: 'text', code: homeCli }} compact />
          </div>
          <div className="demo-report">
            <div className="report-header">
              <span>Run Report</span>
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
            <a href={href('/docs/reports')}>
              查看报告能力 <ArrowRight size={16} />
            </a>
          </div>
        </div>
      </section>

      <section className="product-section product-positioning">
        <div className="section-heading">
          <p className="eyebrow">产品定位</p>
          <h2>从一次接口调试，到可复用的 API 测试资产</h2>
          <p>
            Drun 适合把团队日常接口验证沉淀下来：本地能快速调试，CI 能稳定运行，失败时能直接看到诊断、请求片段和报告证据。
          </p>
        </div>
        <div className="product-pillar-grid">
          {productPillars.map((pillar) => {
            const Icon = pillar.icon;
            return (
              <article className="product-pillar" key={pillar.title}>
                <Icon size={24} />
                <h3>{pillar.title}</h3>
                <p>{pillar.text}</p>
              </article>
            );
          })}
        </div>
      </section>

      <section className="product-section workflow-section">
        <div className="section-heading">
          <p className="eyebrow">工作流</p>
          <h2>写、查、跑、交付，一条路径完成</h2>
          <p>首页先讲产品怎么帮你完成工作，详细语法和实战步骤继续放在文档页里。</p>
        </div>
        <div className="workflow-grid">
          {workflow.map((item) => {
            const Icon = item.icon;
            return (
              <article className="workflow-card" key={item.step}>
                <span>{item.step}</span>
                <Icon size={22} />
                <h3>{item.title}</h3>
                <p>{item.text}</p>
              </article>
            );
          })}
        </div>
      </section>

      <section className="product-section capability-section">
        <div className="section-heading">
          <p className="eyebrow">核心能力</p>
          <h2>围绕 API 测试资产的完整闭环</h2>
        </div>
        <div className="capability-grid">
          {capabilities.map((item) => {
            const Icon = item.icon;
            return (
              <article className="capability-card" key={item.title}>
                <Icon size={22} />
                <div>
                  <h3>{item.title}</h3>
                  <p>{item.text}</p>
                </div>
              </article>
            );
          })}
        </div>
      </section>

      <section className="product-section docs-index">
        <div className="section-heading split-heading">
          <div>
            <p className="eyebrow">产品文档</p>
            <h2>继续深入使用 Drun</h2>
          </div>
          <a className="text-link" href={href('/docs/getting-started')}>
            从快速开始进入 <ArrowRight size={16} />
          </a>
        </div>
        <div className="index-grid">
          {docGroups.map((group) => (
            <article className="index-panel" key={group.title}>
              <h3>{group.title}</h3>
              {group.pages.map((pageId) => {
                const page = pageById(pageId);
                if (!page) {
                  return null;
                }
                return (
                  <a key={page.id} href={href(page.path)}>
                    <span>{page.title}</span>
                    <ArrowRight size={16} />
                  </a>
                );
              })}
            </article>
          ))}
        </div>
      </section>

      <section className="product-section agent-skill-entry">
        <div className="section-heading split-heading">
          <div>
            <p className="eyebrow">AI 协作者</p>
            <h2>让 Agent 稳定写出 Drun YAML 和命令</h2>
            <p>使用仓库内的 drun-usage skill，给 Codex / AI Agent 明确的触发提示词，让它按 Drun DSL 产出可执行方案。</p>
          </div>
          <a className="text-link" href={href('/agent-skill')}>
            查看 Agent Skill <ArrowRight size={16} />
          </a>
        </div>
      </section>

      <section className="product-section reading-path">
        <div className="section-heading">
          <p className="eyebrow">推荐路径</p>
          <h2>第一次使用建议这样读</h2>
        </div>
        <div className="reading-steps">
          {[
            pageById('getting-started'),
            pageById('composition'),
            pageById('troubleshooting'),
            pageById('debug-migration'),
          ].map((page) =>
            page ? (
              <a className="reading-step" href={href(page.path)} key={page.id}>
                <h3>{page.title}</h3>
                <p>{page.description}</p>
                <span>
                  阅读文档 <ArrowRight size={16} />
                </span>
              </a>
            ) : null,
          )}
        </div>
      </section>
    </main>
  );
}

function AgentSkillPage() {
  function scrollToSection(id: string) {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  return (
    <main className="agent-skill-shell">
      <section className="agent-skill-hero">
        <div>
          <p className="eyebrow">Agent Skill</p>
          <h1>{agentSkillContent.title}</h1>
          <p>{agentSkillContent.description}</p>
          <div className="hero-actions">
            <button className="primary-button" type="button" onClick={() => scrollToSection('trigger-prompts')}>
              <Clipboard size={18} />
              复制触发提示词
            </button>
            <a
              className="secondary-button"
              href="https://github.com/Devliang24/drun/blob/main/drun-usage/SKILL.md"
              target="_blank"
              rel="noreferrer"
            >
              <ExternalLink size={18} />
              查看 SKILL.md
            </a>
          </div>
        </div>
        <div className="agent-skill-summary">
          {agentSkillContent.positioning.map((item) => (
            <p key={item}>{item}</p>
          ))}
        </div>
      </section>

      <section className="agent-skill-section">
        <div className="section-heading">
          <p className="eyebrow">触发场景</p>
          <h2>什么时候该点名 drun-usage skill</h2>
        </div>
        <div className="skill-grid">
          {agentSkillContent.triggerScenarios.map((scenario) => (
            <article className="skill-card" key={scenario.title}>
              <CheckCircle2 size={22} />
              <h3>{scenario.title}</h3>
              <p>{scenario.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="agent-skill-section" id="agent-tools">
        <div className="section-heading">
          <p className="eyebrow">使用方式</p>
          <h2>在不同 Agent 中使用 drun-usage</h2>
          <p>不同 Agent 的扩展机制不完全一样，核心都是先让它读取 drun-usage 的规则，再提交具体的 Drun 任务。</p>
        </div>
        <div className="agent-tool-grid">
          {agentSkillContent.agentTools.map((tool) => (
            <article className="agent-tool-card" key={tool.title}>
              <div className="agent-tool-header">
                <h3>{tool.title}</h3>
                <p>{tool.summary}</p>
              </div>
              <div className="agent-tool-body">
                <div className="agent-tool-details">
                  <div className="agent-tool-meta">
                    <strong>最小配置</strong>
                    <dl>
                      <div>
                        <dt>存放位置</dt>
                        <dd>{tool.setup.storagePath}</dd>
                      </div>
                      <div>
                        <dt>需要保留</dt>
                        <dd>{tool.setup.keepFiles}</dd>
                      </div>
                      <div>
                        <dt>轻量用法</dt>
                        <dd>{tool.setup.quickUse}</dd>
                      </div>
                    </dl>
                  </div>
                  <div className="agent-tool-meta">
                    <strong>触发方式</strong>
                    <span>{tool.trigger}</span>
                  </div>
                  <ul>
                    {tool.notes.map((note) => (
                      <li key={note}>{note}</li>
                    ))}
                  </ul>
                </div>
                <CodeBlock sample={{ title: 'Prompt', language: 'text', code: tool.prompt }} compact wrap />
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="agent-skill-section">
        <div className="section-heading split-heading">
          <div>
            <p className="eyebrow">输出规则</p>
            <h2>让 Agent 少猜，多给可执行结果</h2>
          </div>
          <CodeBlock sample={agentSkillContent.sampleOutput} compact />
        </div>
        <div className="skill-rule-grid">
          <article className="skill-rule-panel">
            <h3>默认输出</h3>
            <ul>
              {agentSkillContent.outputRules.map((rule) => (
                <li key={rule}>{rule}</li>
              ))}
            </ul>
          </article>
          <article className="skill-rule-panel">
            <h3>能力边界</h3>
            <ul>
              {agentSkillContent.boundaries.map((rule) => (
                <li key={rule}>{rule}</li>
              ))}
            </ul>
          </article>
        </div>
      </section>

      <section className="agent-skill-section" id="trigger-prompts">
        <div className="section-heading">
          <p className="eyebrow">通用触发提示词</p>
          <h2>复制后直接发给 Agent</h2>
          <p>提示词里明确写出 drun-usage skill，再补接口、链路、错误日志或转换输入，Agent 就能按 Drun 约束组织答案。</p>
        </div>
        <div className="prompt-grid">
          {agentSkillContent.promptExamples.map((example) => (
            <article className="prompt-card" key={example.title}>
              <h3>{example.title}</h3>
              <p>{example.when}</p>
              <CodeBlock sample={{ title: 'Prompt', language: 'text', code: example.prompt }} compact wrap />
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}

function Sidebar({ route }: { route: string }) {
  return (
    <aside className="doc-sidebar" aria-label="文档目录">
      {docGroups.map((group) => (
        <div className="sidebar-group" key={group.title}>
          <p>{group.title}</p>
          {group.pages.map((pageId) => {
            const page = pageById(pageId);
            if (!page) {
              return null;
            }
            return (
              <a className={route === page.path ? 'active' : ''} href={href(page.path)} key={page.id}>
                {page.title}
              </a>
            );
          })}
        </div>
      ))}
    </aside>
  );
}

function MobileDocMenu({ route }: { route: string }) {
  return (
    <details className="mobile-doc-menu">
      <summary>打开文档目录</summary>
      <Sidebar route={route} />
    </details>
  );
}

function OnThisPage({ sections }: { sections: ArticleSection[] }) {
  function jumpTo(id: string) {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  return (
    <aside className="toc" aria-label="本页目录">
      <p>本页目录</p>
      {sections.map((section) => (
        <button type="button" key={section.id} onClick={() => jumpTo(section.id)}>
          {section.title}
        </button>
      ))}
    </aside>
  );
}

function ArticleSectionView({ section }: { section: ArticleSection }) {
  return (
    <section className={`article-section ${section.kind ? `section-${section.kind}` : ''}`} id={section.id}>
      <h2>{section.title}</h2>
      {section.body.map((paragraph) => (
        <p key={paragraph}>{paragraph}</p>
      ))}
      {section.code ? <CodeBlock sample={section.code} /> : null}
    </section>
  );
}

function ArticlePage({ page, route }: { page: ArticlePageType; route: string }) {
  const Icon = page.icon;

  return (
    <main className="docs-shell">
      <MobileDocMenu route={route} />
      <Sidebar route={route} />
      <article className="article">
        <div className="article-hero">
          <Icon size={30} />
          <p className="eyebrow">用户指南</p>
          <h1>{page.title}</h1>
          <p>{page.description}</p>
        </div>
        {page.sections.map((section) => (
          <ArticleSectionView section={section} key={section.id} />
        ))}
      </article>
      <OnThisPage sections={page.sections} />
    </main>
  );
}

function NotFound() {
  return (
    <main className="not-found">
      <h1>没有找到这个页面</h1>
      <p>你可以回到首页，或从快速开始重新进入文档。</p>
      <a className="primary-button" href={href('/docs/getting-started')}>
        阅读快速开始
      </a>
    </main>
  );
}

function Footer() {
  return (
    <footer className="footer">
      <div>
        <strong>Drun</strong>
        <p>中文用户指南文档站。</p>
      </div>
      <div className="footer-links">
        <a href="https://github.com/Devliang24/drun" target="_blank" rel="noreferrer">
          GitHub <ExternalLink size={14} />
        </a>
        <a href={href('/agent-skill')}>
          Agent Skill <ArrowRight size={14} />
        </a>
        <a href="https://github.com/Devliang24/drun/blob/main/README.md" target="_blank" rel="noreferrer">
          English README <ExternalLink size={14} />
        </a>
      </div>
    </footer>
  );
}

export function App() {
  const [route, setRoute] = useState(routeFromHash());
  const currentPage = useMemo(() => findPage(route), [route]);
  const isAgentSkillRoute = route === '/agent-skill';

  useEffect(() => {
    const rawRoute = rawRouteFromHash();
    const redirect = legacyRouteRedirects[rawRoute];
    if (redirect) {
      window.location.replace(`${window.location.pathname}${window.location.search}#${redirect}`);
    }
  }, []);

  useEffect(() => {
    function onHashChange() {
      const rawRoute = rawRouteFromHash();
      const redirect = legacyRouteRedirects[rawRoute];
      if (redirect) {
        window.location.replace(`${window.location.pathname}${window.location.search}#${redirect}`);
        return;
      }
      setRoute(routeFromHash());
      window.scrollTo({ top: 0 });
    }

    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  useEffect(() => {
    document.title = currentPage
      ? `${currentPage.title} | Drun 文档站`
      : isAgentSkillRoute
        ? 'Agent Skill | Drun 文档站'
        : 'Drun 文档站';
  }, [currentPage, isAgentSkillRoute]);

  return (
    <div className="app-shell">
      <Header route={route} />
      {route === '/' ? (
        <HomePage />
      ) : isAgentSkillRoute ? (
        <AgentSkillPage />
      ) : currentPage ? (
        <ArticlePage page={currentPage} route={route} />
      ) : (
        <NotFound />
      )}
      <Footer />
    </div>
  );
}
