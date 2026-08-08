function I({ children, size = 16, className, strokeWidth = 1.8 }) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

export const IconSearch = (p) => (
  <I {...p}>
    <circle cx="11" cy="11" r="7" />
    <path d="m21 21-4.3-4.3" />
  </I>
);

export const IconBox = (p) => (
  <I {...p}>
    <path d="M21 8.5v7a2 2 0 0 1-1 1.73l-7 4a2 2 0 0 1-2 0l-7-4A2 2 0 0 1 3 15.5v-7a2 2 0 0 1 1-1.73l7-4a2 2 0 0 1 2 0l7 4a2 2 0 0 1 1 1.73Z" />
    <path d="M3.3 7.3 12 12l8.7-4.7" />
    <path d="M12 22V12" />
  </I>
);

export const IconCode = (p) => (
  <I {...p}>
    <path d="m8 6-6 6 6 6" />
    <path d="m16 6 6 6-6 6" />
    <path d="m14 4-4 16" />
  </I>
);

export const IconTag = (p) => (
  <I {...p}>
    <path d="M12.6 2.6 21 11a2 2 0 0 1 0 2.8l-7.2 7.2a2 2 0 0 1-2.8 0L2.6 12.6A2 2 0 0 1 2 11.2V5a3 3 0 0 1 3-3h6.2a2 2 0 0 1 1.4.6Z" />
    <circle cx="7.5" cy="7.5" r="1" />
  </I>
);

export const IconLayers = (p) => (
  <I {...p}>
    <path d="m12 2 9 4.5-9 4.5-9-4.5Z" />
    <path d="m3 12 9 4.5L21 12" />
    <path d="m3 16.5 9 4.5 9-4.5" />
  </I>
);

export const IconWallet = (p) => (
  <I {...p}>
    <path d="M21 12V7a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h15a2 2 0 0 0 2-2v-5Z" />
    <path d="M21 12h-4a2 2 0 0 0 0 4h4" />
    <circle cx="16.5" cy="14" r="0.5" fill="currentColor" />
  </I>
);

export const IconBolt = (p) => (
  <I {...p}>
    <path d="M13 2 4.5 13.5H11L10 22l8.5-11.5H13L13 2Z" />
  </I>
);

export const IconSliders = (p) => (
  <I {...p}>
    <path d="M4 6h16M4 12h16M4 18h16" />
    <circle cx="9" cy="6" r="2" fill="var(--sliders-bg, none)" />
    <circle cx="15" cy="12" r="2" fill="var(--sliders-bg, none)" />
    <circle cx="7" cy="18" r="2" fill="var(--sliders-bg, none)" />
  </I>
);

export const IconRefresh = (p) => (
  <I {...p}>
    <path d="M21 12a9 9 0 1 1-2.64-6.36" />
    <path d="M21 3v6h-6" />
  </I>
);

export const IconX = (p) => (
  <I {...p}>
    <path d="M18 6 6 18M6 6l12 12" />
  </I>
);

export const IconArrowUpRight = (p) => (
  <I {...p}>
    <path d="M7 17 17 7" />
    <path d="M8 7h9v9" />
  </I>
);

export const IconMessage = (p) => (
  <I {...p}>
    <path d="M21 12a8 8 0 0 1-8 8H4l2-3a8 8 0 1 1 15-5Z" />
  </I>
);

export const IconCalendar = (p) => (
  <I {...p}>
    <rect x="3" y="5" width="18" height="16" rx="2" />
    <path d="M16 3v4M8 3v4M3 11h18" />
  </I>
);

export const IconClock = (p) => (
  <I {...p}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 7v5l3 3" />
  </I>
);

export const IconStar = (p) => (
  <I {...p}>
    <path d="m12 3 2.9 5.9 6.6 1-4.7 4.6 1.1 6.5L12 17.8l-5.9 3.2 1.1-6.5L2.5 9.9l6.6-1L12 3Z" />
  </I>
);

export const IconFlame = (p) => (
  <I {...p}>
    <path d="M12 3s5 4.5 5 9.5A5 5 0 0 1 7 12.5C7 9 12 3 12 3Z" />
    <path d="M12 21a5 5 0 0 1-5-5c0-1 .3-2 .8-2.9C8.7 14 11 15 12 17c1-2 3.3-3 4.2-3.9.5.9.8 1.9.8 2.9a5 5 0 0 1-5 5Z" />
  </I>
);

export const IconChevronDown = (p) => (
  <I {...p}>
    <path d="m6 9 6 6 6-6" />
  </I>
);

export const IconChevronUp = (p) => (
  <I {...p}>
    <path d="m6 15 6-6 6 6" />
  </I>
);

export const IconFilter = (p) => (
  <I {...p}>
    <path d="M3 5h18M6 12h12M10 19h4" />
  </I>
);

export const IconTrend = (p) => (
  <I {...p}>
    <path d="M3 17l6-6 4 4 8-8" />
    <path d="M15 7h6v6" />
  </I>
);

export const IconDollar = (p) => (
  <I {...p}>
    <path d="M12 3v18" />
    <path d="M17 6.5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
  </I>
);

export const IconCheck = (p) => (
  <I {...p}>
    <path d="m5 13 4 4L19 7" />
  </I>
);

export const IconInbox = (p) => (
  <I {...p}>
    <path d="M22 12h-6l-2 3h-4l-2-3H2" />
    <path d="M5.5 5.5 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.5-6.5A2 2 0 0 0 16.8 4H7.2a2 2 0 0 0-1.7 1.5Z" />
  </I>
);

export const IconGlobe = (p) => (
  <I {...p}>
    <circle cx="12" cy="12" r="9" />
    <path d="M3 12h18" />
    <path d="M12 3a13.5 13.5 0 0 1 0 18 13.5 13.5 0 0 1 0-18Z" />
  </I>
);

export const IconShield = (p) => (
  <I {...p}>
    <path d="M12 3 5 6v5c0 4.5 3 8.3 7 10 4-1.7 7-5.5 7-10V6l-7-3Z" />
    <path d="m9 12 2 2 4-4" />
  </I>
);

export const IconSparkles = (p) => (
  <I {...p}>
    <path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M18.4 5.6l-2.8 2.8M8.4 15.6l-2.8 2.8" />
  </I>
);
