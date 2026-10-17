import type {ReactNode} from 'react';
import Heading from '@theme/Heading';
import styles from './styles.module.css';

type FeatureItem = {
  title: string;
  icon: ReactNode;
  description: ReactNode;
};

const FeatureList: FeatureItem[] = [
  {
    title: 'Concurrent by construction',
    icon: (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true">
        <path d="M13 2 3 14h7l-1 8 10-12h-7l1-8z" />
      </svg>
    ),
    description: (
      <>
        Pass all source files, in any order — Lemon discovers module
        dependencies and compiles independent files in parallel across a fixed
        worker pool.
      </>
    ),
  },
  {
    title: 'Embedded toolchain',
    icon: (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true">
        <rect x="5" y="5" width="14" height="14" rx="2" />
        <rect x="9.5" y="9.5" width="5" height="5" />
        <path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3" />
      </svg>
    ),
    description: (
      <>
        Reason parsing, the React JSX transform, and the Melange JS driver all
        run in-process. No <code>refmt</code>, no <code>melc</code>, no{' '}
        <code>-pp</code>, no external PPX subprocesses.
      </>
    ),
  },
  {
    title: 'Three targets',
    icon: (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true">
        <circle cx="12" cy="12" r="10" />
        <circle cx="12" cy="12" r="6" />
        <circle cx="12" cy="12" r="2" />
      </svg>
    ),
    description: (
      <>
        Bytecode and native executables, plus ES-module JavaScript output with
        staged, atomic publication guarded by an ownership marker.
      </>
    ),
  },
  {
    title: 'Reason + React',
    icon: (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true">
        <circle cx="12" cy="12" r="1" fill="currentColor" />
        <path d="M20.2 20.2c2.04-2.03.02-7.36-4.5-11.9-4.54-4.52-9.87-6.54-11.9-4.5-2.04 2.03-.02 7.36 4.5 11.9 4.54 4.52 9.87 6.54 11.9 4.5Z" />
        <path d="M15.7 15.7c4.52-4.54 6.54-9.87 4.5-11.9-2.03-2.04-7.36-.02-11.9 4.5-4.52 4.54-6.54 9.87-4.5 11.9 2.03 2.04 7.36.02 11.9-4.5Z" />
      </svg>
    ),
    description: (
      <>
        <code>.re/.rei</code> sources for every target. Add{' '}
        <code>--react</code> for the in-process JSX transform and the pinned{' '}
        <code>react</code>/<code>react-dom</code> runtimes bundled into the
        output.
      </>
    ),
  },
  {
    title: 'Proven end-to-end',
    icon: (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true">
        <path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z" />
        <path d="m9 12 2 2 4-4" />
      </svg>
    ),
    description: (
      <>
        Every CI scenario compiles <em>and executes</em> a real artifact — on
        Linux, macOS ARM/Intel, and Windows. A failed build never replaces a
        successful output.
      </>
    ),
  },
  {
    title: 'Ships everywhere',
    icon: (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true">
        <path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z" />
        <path d="m3.3 7 8.7 5 8.7-5" />
        <path d="M12 22V12" />
      </svg>
    ),
    description: (
      <>
        Relocatable, self-contained tarballs and zips, Homebrew bottles, and a
        winget manifest — all built and validated by the release workflow.
      </>
    ),
  },
];

function Feature({title, icon, description}: FeatureItem) {
  return (
    <div className="col col--4">
      <div className={`card ${styles.featureCard}`}>
        <div className={`card__header ${styles.featureHeader}`}>
          <span className={styles.featureIcon}>{icon}</span>
          <Heading as="h3" className={styles.featureTitle}>
            {title}
          </Heading>
        </div>
        <div className="card__body">
          <p className={styles.featureText}>{description}</p>
        </div>
      </div>
    </div>
  );
}

export default function HomepageFeatures(): JSX.Element {
  return (
    <section className={styles.features}>
      <div className="container">
        <Heading as="h2" className={styles.sectionTitle}>
          Why Lemon?
        </Heading>
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
