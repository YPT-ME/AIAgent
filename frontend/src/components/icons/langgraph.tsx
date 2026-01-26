export function LangGraphLogoSVG({
  className,
  width,
  height,
}: {
  width?: number;
  height?: number;
  className?: string;
}) {
  return (
    <img
      src="/logo.svg"
      alt="Logo"
      width={width}
      height={height}
      className={className}
      style={{
        width: width ? `${width}px` : undefined,
        height: height ? `${height}px` : undefined,
      }}
    />
  );
}
