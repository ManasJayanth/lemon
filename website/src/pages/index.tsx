import Link from '@docusaurus/Link';
import useBaseUrl from '@docusaurus/useBaseUrl';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Heading from '@theme/Heading';
import clsx from 'clsx';
import HomepageFeatures from '@site/src/components/HomepageFeatures';
import styles from './index.module.css';

function TerminalLine({prompt, children}) {
  return (
    <div className={styles.terminalLine}>
      {prompt ? (
        <span className={styles.terminalPrompt}>$</span>
      ) : (
        <span className={styles.terminalSpacer}> </span>
      )}
      <span className={prompt ? styles.terminalCmd : styles.terminalOut}>
        {children}
      </span>
    </div>
  );
}

function Terminal() {
  return (
    <div className={styles.terminal}>
      <div className={styles.terminalBar}>
        <span className={clsx(styles.dot, styles.dotRed)} />
        <span className={clsx(styles.dot, styles.dotYellow)} />
        <span className={clsx(styles.dot, styles.dotGreen)} />
        <span className={styles.terminalTitle}>lemon — sh</span>
      </div>
      <div className={styles.terminalBody}>
        <TerminalLine prompt>
          lemon build -j 4 -o hello.byte examples/hello.ml
        </TerminalLine>
        <TerminalLine>
          <span className={styles.terminalOk}>✓</span> compiling{' '}
          <span className={styles.terminalEm}>hello.ml</span> · 4 workers
        </TerminalLine>
        <TerminalLine>
          <span className={styles.terminalOk}>✓</span> linked{' '}
          <span className={styles.terminalEm}>hello.byte</span>
        </TerminalLine>
        <TerminalLine prompt>./hello.byte</TerminalLine>
        <TerminalLine>
          <span className={styles.terminalLemon}>Hello, world! 🍋</span>
        </TerminalLine>
      </div>
    </div>
  );
}

export default function Home(): JSX.Element {
  const {siteConfig} = useDocusaurusContext();
  return (
    <main>
      <section className={styles.hero}>
        <div className="container">
          <div className={styles.heroInner}>
            <img
              src={useBaseUrl('img/logo.svg')}
              alt="Lemon logo"
              className={styles.heroLogo}
            />
            <Heading as="h1" className={styles.heroTitle}>
              Lemon
            </Heading>
            <p className={styles.heroTagline}>{siteConfig.tagline}</p>
            <p className={styles.heroSub}>
              Pass all your source files, in any order — Lemon discovers the
              module graph and compiles independent files concurrently.
              Bytecode, native, and JavaScript targets, with embedded Reason
              and React JSX support.
            </p>
            <div className={styles.heroBadges}>
              <span className={styles.badge}>OCaml</span>
              <span className={styles.badge}>Reason</span>
              <span className={styles.badge}>Melange</span>
              <span className={styles.badge}>React</span>
            </div>
            <div className={styles.heroButtons}>
              <Link
                className={clsx('button button--lg', styles.heroCta)}
                to="/docs/intro">
                Get Started
              </Link>
              <Link
                className="button button--lg button--outline button--secondary"
                href="https://github.com/ManasJayanth/lemon">
                View on GitHub
              </Link>
            </div>
          </div>
          <Terminal />
        </div>
      </section>
      <HomepageFeatures />
    </main>
  );
}
