import type { ButtonHTMLAttributes, ReactNode } from "react";

type ButtonVariant = "primary" | "ghost" | "danger";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
  icon?: ReactNode;
  variant?: ButtonVariant;
};

export function Button({
  children,
  icon,
  variant = "ghost",
  className,
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      {...props}
      className={["button", `button--${variant}`, className].filter(Boolean).join(" ")}
      type={type}
    >
      {icon}
      <span>{children}</span>
    </button>
  );
}
