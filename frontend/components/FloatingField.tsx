"use client";

import {
  useState,
  type ChangeEventHandler,
  type ReactNode,
  type SelectHTMLAttributes,
} from "react";

type FloatingTextInputProps = {
  id: string;
  label: string;
  value: string;
  onChange: ChangeEventHandler<HTMLInputElement>;
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  autoComplete?: string;
  type?: "text" | "search";
  labelAction?: ReactNode;
};

type FloatingSelectProps = {
  id: string;
  label: string;
  value: string;
  onChange: ChangeEventHandler<HTMLSelectElement>;
  children: ReactNode;
  required?: boolean;
  disabled?: boolean;
} & Pick<SelectHTMLAttributes<HTMLSelectElement>, "aria-label">;

const fieldBaseClass =
  "h-11 w-full rounded-md border border-line bg-surface py-2 text-base leading-6 text-ink placeholder:text-muted shadow-sm transition focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/40 disabled:cursor-not-allowed disabled:bg-bg disabled:text-muted sm:text-sm sm:leading-5";
const floatingLabelBaseClass =
  "absolute left-3 z-[1] truncate bg-surface px-1 transition-all duration-150";
const floatingLabelClass =
  "top-0 -translate-y-1/2 text-[11px] leading-4 text-ink-soft";
const restingLabelClass =
  "top-1/2 -translate-y-1/2 text-sm leading-5 text-muted";

function requiredMark(required: boolean): ReactNode {
  return required ? <span className="text-danger"> *</span> : null;
}

export function FloatingTextInput({
  id,
  label,
  value,
  onChange,
  placeholder,
  required = false,
  disabled = false,
  autoComplete = "off",
  type = "text",
  labelAction,
}: FloatingTextInputProps) {
  const [focused, setFocused] = useState(false);
  const floated = focused || value.trim().length > 0 || Boolean(placeholder);
  const labelWidthClass = labelAction
    ? "max-w-[calc(100%-4.5rem)]"
    : "max-w-[calc(100%-1.5rem)]";
  const inputPaddingClass = labelAction ? "pl-3 pr-12" : "px-3";

  return (
    <div className="relative">
      <input
        id={id}
        type={type}
        className={`${fieldBaseClass} ${inputPaddingClass}`}
        value={value}
        onChange={onChange}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        placeholder={placeholder}
        required={required}
        disabled={disabled}
        autoComplete={autoComplete}
      />
      <label
        htmlFor={id}
        className={`${floatingLabelBaseClass} ${labelWidthClass} ${
          floated ? floatingLabelClass : restingLabelClass
        }`}
      >
        {label}
        {requiredMark(required)}
      </label>
      {labelAction && (
        <div className="absolute right-2 top-1/2 -translate-y-1/2">
          {labelAction}
        </div>
      )}
    </div>
  );
}

export function FloatingSelect({
  id,
  label,
  value,
  onChange,
  children,
  required = false,
  disabled = false,
  "aria-label": ariaLabel,
}: FloatingSelectProps) {
  return (
    <div className="relative">
      <select
        id={id}
        className={`${fieldBaseClass} appearance-none px-3`}
        value={value}
        onChange={onChange}
        required={required}
        disabled={disabled}
        aria-label={ariaLabel}
      >
        {children}
      </select>
      <label
        htmlFor={id}
        className={`${floatingLabelBaseClass} ${floatingLabelClass} max-w-[calc(100%-2.5rem)]`}
      >
        {label}
        {requiredMark(required)}
      </label>
    </div>
  );
}
