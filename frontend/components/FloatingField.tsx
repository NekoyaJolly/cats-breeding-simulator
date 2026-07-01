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
  "h-11 w-full rounded-md border border-slate-300 bg-white pb-1.5 pt-4 text-sm shadow-sm transition focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400";
const floatingLabelBaseClass =
  "absolute left-3 z-10 truncate bg-white px-1 transition-all duration-150";
const floatingLabelClass = "top-1 text-[11px] leading-4 text-slate-500";
const restingLabelClass =
  "top-1/2 -translate-y-1/2 text-sm leading-5 text-slate-500";

function requiredMark(required: boolean): ReactNode {
  return required ? <span className="text-red-500"> *</span> : null;
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
  const rightInsetClass = labelAction ? "right-14" : "right-3";
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
        className={`${floatingLabelBaseClass} ${rightInsetClass} ${
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
        className={`${floatingLabelBaseClass} ${floatingLabelClass} right-8`}
      >
        {label}
        {requiredMark(required)}
      </label>
    </div>
  );
}
