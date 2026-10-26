const PATHS = {
  arrow: <path d="M5 12h14m-5-5 5 5-5 5" />,
  chevron: <path d="m6 9 6 6 6-6" />,
  bookmark: <path d="M6 4h12v17l-6-4-6 4z" />,
  close: <path d="M6 6l12 12M18 6 6 18" />,
  check: <path d="m5 12 5 5L20 7" />,
  refresh: (
    <>
      <path d="M20 12a8 8 0 1 1-2.34-5.66" />
      <path d="M20 4v5h-5" />
    </>
  ),
  alert: (
    <>
      <path d="M12 3 2.5 20h19L12 3Z" />
      <path d="M12 10v4M12 17.5v.5" />
    </>
  ),
  spark: (
    <>
      <path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5z" />
      <path d="m20 2 .6 1.4L22 4l-1.4.6L20 6l-.6-1.4L18 4l1.4-.6z" />
    </>
  ),
  search: (
    <>
      <circle cx="10.5" cy="10.5" r="6.5" />
      <path d="m16 16 4 4" />
    </>
  ),
  grid: (
    <>
      <rect x="3" y="3" width="7" height="7" rx="2" />
      <rect x="14" y="3" width="7" height="7" rx="2" />
      <rect x="3" y="14" width="7" height="7" rx="2" />
      <rect x="14" y="14" width="7" height="7" rx="2" />
    </>
  ),
  exit: <path d="M9 4H4v16h5m5-12 4 4-4 4m-5-4h11" />,
  link: <path d="M14 3h7v7m0-7L10 14M10 4H4v16h16v-6" />,
  send: <path d="m3 3 18 9-18 9 3-9-3-9Zm3 9h15" />,
  building: <path d="M4 21V3h12v18M2 21h20M16 9h4v12M8 7h4M8 11h4M8 15h4" />,
  eye: (
    <>
      <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7S2 12 2 12Z" />
      <circle cx="12" cy="12" r="3" />
    </>
  ),
  eyeOff: (
    <>
      <path d="M3 3l18 18" />
      <path d="M10.6 10.6a3 3 0 0 0 4.2 4.2" />
      <path d="M9.9 5.2A10.9 10.9 0 0 1 12 5c7 0 10 7 10 7a17.4 17.4 0 0 1-3.2 4.2M6.6 6.6C3.9 8.5 2 12 2 12s3 7 10 7c1.6 0 3-.3 4.3-.9" />
    </>
  ),
};

export default function Icon({ name, size = 20, className, ...props }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      className={className}
      {...props}
    >
      {PATHS[name] ?? null}
    </svg>
  );
}
