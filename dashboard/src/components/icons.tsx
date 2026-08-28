type IconProps = { className?: string };

const base = "stroke-current fill-none";

export function IconGrid({ className }: IconProps) {
  return (
    <svg viewBox="0 0 20 20" className={className} strokeWidth="1.5">
      <rect x="2.5" y="2.5" width="6" height="6" rx="1" className={base} />
      <rect x="11.5" y="2.5" width="6" height="6" rx="1" className={base} />
      <rect x="2.5" y="11.5" width="6" height="6" rx="1" className={base} />
      <rect x="11.5" y="11.5" width="6" height="6" rx="1" className={base} />
    </svg>
  );
}

export function IconBuilding({ className }: IconProps) {
  return (
    <svg viewBox="0 0 20 20" className={className} strokeWidth="1.5">
      <rect x="4" y="2.5" width="12" height="15" rx="1" className={base} />
      <line x1="7" y1="6" x2="9" y2="6" className={base} />
      <line x1="11" y1="6" x2="13" y2="6" className={base} />
      <line x1="7" y1="9.5" x2="9" y2="9.5" className={base} />
      <line x1="11" y1="9.5" x2="13" y2="9.5" className={base} />
      <line x1="7" y1="13" x2="9" y2="13" className={base} />
      <line x1="11" y1="13" x2="13" y2="13" className={base} />
    </svg>
  );
}

export function IconHeadset({ className }: IconProps) {
  return (
    <svg viewBox="0 0 20 20" className={className} strokeWidth="1.5">
      <path d="M4 11v-1a6 6 0 0 1 12 0v1" className={base} strokeLinecap="round" />
      <rect x="2.5" y="10.5" width="3" height="5" rx="1" className={base} />
      <rect x="14.5" y="10.5" width="3" height="5" rx="1" className={base} />
      <path d="M14.5 15.5v.5a2 2 0 0 1-2 2h-2" className={base} strokeLinecap="round" />
    </svg>
  );
}

export function IconKey({ className }: IconProps) {
  return (
    <svg viewBox="0 0 20 20" className={className} strokeWidth="1.5">
      <circle cx="6.5" cy="13.5" r="3" className={base} />
      <path d="M8.7 11.3 15 5l1.5 1.5M13 7.5 14.5 9" className={base} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function IconLogout({ className }: IconProps) {
  return (
    <svg viewBox="0 0 20 20" className={className} strokeWidth="1.5">
      <path d="M8 3.5H5a1.5 1.5 0 0 0-1.5 1.5v10A1.5 1.5 0 0 0 5 16.5h3" className={base} strokeLinecap="round" />
      <path d="M12.5 13.5 16.5 10l-4-3.5M16 10H7.5" className={base} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function IconPlus({ className }: IconProps) {
  return (
    <svg viewBox="0 0 20 20" className={className} strokeWidth="1.8">
      <path d="M10 4v12M4 10h12" className={base} strokeLinecap="round" />
    </svg>
  );
}

export function IconChevronRight({ className }: IconProps) {
  return (
    <svg viewBox="0 0 20 20" className={className} strokeWidth="1.8">
      <path d="M7.5 4.5 13 10l-5.5 5.5" className={base} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function IconCheck({ className }: IconProps) {
  return (
    <svg viewBox="0 0 20 20" className={className} strokeWidth="2">
      <path d="M4.5 10.5 8 14l7.5-8" className={base} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function IconUpload({ className }: IconProps) {
  return (
    <svg viewBox="0 0 20 20" className={className} strokeWidth="1.5">
      <path d="M10 13V4M6.5 7.5 10 4l3.5 3.5" className={base} strokeLinecap="round" strokeLinejoin="round" />
      <path d="M4 14v1.5A1.5 1.5 0 0 0 5.5 17h9a1.5 1.5 0 0 0 1.5-1.5V14" className={base} strokeLinecap="round" />
    </svg>
  );
}
