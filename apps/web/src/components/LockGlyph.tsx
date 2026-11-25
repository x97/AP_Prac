export function LockGlyph({
  size = 10,
  className = "",
}: {
  size?: number;
  className?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 12 12"
      fill="none"
      className={className}
      aria-hidden="true"
      focusable="false"
    >
      <rect
        x="2"
        y="5.2"
        width="8"
        height="5.6"
        rx="1.3"
        stroke="currentColor"
        strokeWidth="1.2"
      />
      <path
        d="M4 5.2V3.9a2 2 0 1 1 4 0v1.3"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
      />
    </svg>
  );
}
