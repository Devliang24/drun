import { useEffect, useMemo, useState } from 'react';
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
  docGroups,
  docPages,
  featureCards,
  findPage,
  homeCli,
  homeYaml,
  pageById,
  tutorialCards,
  tutorialPages,
  type ArticlePage as ArticlePageType,
  type ArticleSection,
  type CodeSample,
} from './content';

function routeFromHash() {
  const raw = window.location.hash.replace(/^#/, '');
  if (!raw || raw === '/') {
    return '/';
  }
  return raw.startsWith('/') ? raw : `/${raw}`;
}

function href(path: string) {
  return `#${path}`;
}

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
    { label: '教程', path: '/tutorials/first-case' },
    { label: '排障', path: '/docs/troubleshooting' },
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
    if (path.startsWith('/tutorials')) {
      return route.startsWith('/tutorials');
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
  return (
    <main>
      <section className="home-hero">
        <div className="hero-copy">
          <p className="eyebrow">YAML 驱动的 HTTP API 测试框架</p>
          <h1>Drun 用户教程</h1>
          <p className="lead">
            从第一个 Case 到登录后链路、参数化、报告输出和 YAML 排障，按真实使用路径学习 Drun。
          </p>
          <div className="hero-actions">
            <a className="primary-button" href={href('/docs/getting-started')}>
              <BookOpen size={18} />
              从快速开始读起
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

        <div className="hero-preview" aria-label="Drun 示例预览">
          <div className="preview-card preview-yaml">
            <div className="panel-title">testcases/test_user_api.yaml</div>
            <CodeBlock sample={{ language: 'yaml', code: homeYaml }} compact />
          </div>
          <div className="preview-stack">
            <div className="preview-card">
              <div className="panel-title">CLI</div>
              <CodeBlock sample={{ language: 'text', code: homeCli }} compact />
            </div>
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

      <section className="home-section">
        <div className="section-heading">
          <p className="eyebrow">学习路径</p>
          <h2>不是单页介绍，而是能跟着写的用户指南</h2>
        </div>
        <div className="feature-grid compact-grid">
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

      <section className="home-section docs-index">
        <div className="section-heading">
          <p className="eyebrow">文档目录</p>
          <h2>按阶段查用法</h2>
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

      <section className="home-section tutorials-index">
        <div className="section-heading">
          <p className="eyebrow">教程博客</p>
          <h2>按真实工作流练习</h2>
        </div>
        <div className="tutorial-list">
          {tutorialCards.map((tutorial) => (
            <a className="tutorial-link-card" href={href(tutorial.path)} key={tutorial.id}>
              <h3>{tutorial.title}</h3>
              <p>{tutorial.description}</p>
              <span>
                阅读教程 <ArrowRight size={16} />
              </span>
            </a>
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
      <div className="sidebar-group">
        <p>教程博客</p>
        {tutorialPages.map((page) => (
          <a className={route === page.path ? 'active' : ''} href={href(page.path)} key={page.id}>
            {page.title}
          </a>
        ))}
      </div>
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
          <p className="eyebrow">{route.startsWith('/tutorials') ? '教程博客' : '用户指南'}</p>
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
        <p>中文用户教程文档站。</p>
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
  const [route, setRoute] = useState(routeFromHash());
  const currentPage = useMemo(() => findPage(route), [route]);

  useEffect(() => {
    function onHashChange() {
      setRoute(routeFromHash());
      window.scrollTo({ top: 0 });
    }

    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  useEffect(() => {
    document.title = currentPage ? `${currentPage.title} | Drun 文档站` : 'Drun 文档站';
  }, [currentPage]);

  return (
    <div className="app-shell">
      <Header route={route} />
      {route === '/' ? <HomePage /> : currentPage ? <ArticlePage page={currentPage} route={route} /> : <NotFound />}
      <Footer />
    </div>
  );
}
