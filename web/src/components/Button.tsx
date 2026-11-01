import { forwardRef } from "react";
import type { ButtonHTMLAttributes } from "react";
import { cva } from "class-variance-authority";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

const variants = cva("button", {
  variants: {
    variant: {
      primary: "button-primary",
      secondary: "button-secondary",
      ghost: "button-ghost",
    },
  },
  defaultVariants: { variant: "primary" },
});
export const Button = forwardRef<
  HTMLButtonElement,
  ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: "primary" | "secondary" | "ghost";
  }
>(function Button({ className, variant, ...props }, ref) {
  return (
    <button
      ref={ref}
      className={twMerge(clsx(variants({ variant }), className))}
      {...props}
    />
  );
});
