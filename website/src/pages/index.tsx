import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Heading from '@theme/Heading';

export default function Home(): JSX.Element {
  const {siteConfig} = useDocusaurusContext();
  return (
    <main className="container margin-vert--xl text--center">
      <Heading as="h1" className="hero__title">
        🍋 {siteConfig.title}
      </Heading>
      <p className="hero__subtitle">{siteConfig.tagline}</p>
      <p>
        Pass all your source files, in any order — Lemon discovers module
        dependencies and compiles independent files concurrently. Bytecode,
        native, and JavaScript targets, with embedded Reason and React JSX
        support. No refmt, no melc, no external PPX processes.
      </p>
      <div className="button-group">
        <Link className="button button--primary button--lg" to="/docs/intro">
          Get Started
        </Link>
        <Link
          className="button button--secondary button--lg"
          to="/docs/getting-started">
          Build something in 5 minutes
        </Link>
      </div>
    </main>
  );
}
