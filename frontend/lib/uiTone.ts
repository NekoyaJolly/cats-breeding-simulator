// 複数画面で使う UI トーンを集約し、父/母の色味が画面ごとにずれないようにする。

export const PARENT_FIELD_ACCENT_CLASS = {
  sire: "border-sky-100 bg-sky-50/35 shadow-sky-100/60",
  dam: "border-rose-100 bg-rose-50/35 shadow-rose-100/60",
} as const;

export const PARENT_GROUP_ACCENT_CLASS = {
  sire: "border-sky-100 bg-sky-50/35",
  dam: "border-rose-100 bg-rose-50/35",
} as const;
