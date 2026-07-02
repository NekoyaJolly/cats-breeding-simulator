/** UIで利用する表示言語。 */
export type Language = "ja" | "en";

export const LANGUAGE_STORAGE_KEY = "ccp:language";

export const LANGUAGE_OPTIONS = [
  { value: "ja", label: "日本語" },
  { value: "en", label: "English" },
] as const satisfies ReadonlyArray<{ value: Language; label: string }>;

export function isLanguage(value: string | null): value is Language {
  return value === "ja" || value === "en";
}

export function languageFromBrowser(browserLanguage: string): Language {
  return browserLanguage.toLowerCase().startsWith("ja") ? "ja" : "en";
}

export const UI_TEXT = {
  ja: {
    app: {
      name: "Cat Coat Planner",
      subtitle: "猫の色柄シミュレーター",
      languageLabel: "表示言語",
      japanese: "日本語",
      english: "English",
    },
    feedback: {
      trigger: "フィードバックを送る",
      title: "フィードバック",
      description: "ご意見・ご要望をお聞かせください（最大",
      descriptionSuffix: "文字）。",
      placeholder: "気づいたこと・改善してほしいことなど",
      error: "送信に失敗しました。時間をおいて再度お試しください。",
      sent: "送信しました。ありがとうございます！",
      cancel: "キャンセル",
      sending: "送信中…",
      send: "送信",
    },
    tabs: {
      parent: {
        title: "親猫の色柄から予測",
        description:
          "父猫・母猫の色柄を選択して、子猫に出る可能性のある色柄と出現率を確認できます。",
      },
      target: {
        title: "希望カラーに合う組み合わせを探す",
        description:
          "目標にしたい色柄を選択して、その色柄が生まれる可能性のある親猫の組み合わせを探します。",
      },
      kitten: {
        title: "生まれた子猫の色柄から見直す",
        description:
          "実際に生まれた子猫たちの色柄から、父猫・母猫の隠れキャリア候補を推定します。",
      },
    },
    onboarding: {
      helpButton: "使い方",
      progress: "{{current}} / {{total}}",
      next: "次へ",
      previous: "戻る",
      done: "完了",
      skip: "スキップ",
      skipTour: "チュートリアルをスキップ",
      close: "閉じる",
      steps: {
        tabs: {
          title: "目的に合わせてタブを切り替えます",
          description:
            "予測、目標カラーの逆引き、産子実績からの推定を同じ画面で使い分けます。",
        },
        parent: {
          title: "まずは父猫・母猫から予測します",
          description:
            "父猫と母猫の色柄を入れると、子猫に出る可能性のある色柄と割合を確認できます。",
        },
        carriers: {
          title: "検査済み因子だけを追加します",
          description:
            "ここに入れるのは検査や根拠で確認できた因子です。産子からの推定は Kitten Coats で別に確認します。",
        },
        targetTab: {
          title: "目標カラーから探す画面へ進みます",
          description:
            "作りたい色柄が先に決まっているときは、Target Coat から組み合わせを探します。",
        },
        target: {
          title: "最初に目標色柄を選びます",
          description:
            "目標色柄と性別を選ぶと、登録した父猫・母猫から成立しそうな組み合わせを比較できます。",
        },
        kittenTab: {
          title: "生まれた子猫で見直します",
          description:
            "実績が出た後は Kitten Coats で、両親が持つ隠れ因子の候補を絞り込みます。",
        },
        kitten: {
          title: "産子実績からキャリアを推定します",
          description:
            "父母と子猫の色柄を入れると、次回の交配判断に使える推定キャリアを確認できます。",
        },
        help: {
          title: "迷ったらいつでも再表示できます",
          description:
            "このボタンから、同じチュートリアルを何度でも開けます。",
        },
      },
    },
    common: {
      breed: "猫種 (任意)",
      sex: "性別",
      female: "♀ メス",
      male: "♂ オス",
      femaleCandidate: "♀ 母猫候補",
      maleCandidate: "♂ 父猫候補",
      any: "指定なし",
      delete: "削除",
      edit: "編集",
      remove: "登録から外す",
      cancel: "キャンセル",
      update: "更新する",
      recent: "最近の選択",
      femaleOnly: "♀ 限定",
      geneticsAffects: "遺伝に影響",
    },
    parentForm: {
      sireCoat: "父猫の色柄",
      damCoat: "母猫の色柄",
      sirePlaceholder: "例: Silver Tabby / シルバータビー",
      damPlaceholder: "例: Brown Tabby / ブラウンタビー",
      breedPlaceholder: "例: Abyssinian / アビシニアン",
      mode: "計算モード",
      modes: {
        normal: "通常 (normal)",
        explicitCarrier: "明示キャリア (explicit_carrier)",
        carrierExploration: "全キャリア探索 (carrier_exploration)",
      },
      carrierHelp:
        "隠れキャリアを「座位:遺伝子型」のカンマ区切りで指定 (例:",
      sireCarriers: "父猫のキャリア",
      damCarriers: "母猫のキャリア",
      carrierSelector: {
        buttonLabel: "遺伝子座設定",
        configured: "設定中",
        sireButton: "父猫の遺伝子座設定を開く",
        damButton: "母猫の遺伝子座設定を開く",
        sireTitle: "父猫の遺伝子座設定",
        damTitle: "母猫の遺伝子座設定",
        description:
          "確認済みの座位だけを指定します。未指定の座位は通常計算のまま扱います。",
        modeNote:
          "座位を1つでも指定すると、明示キャリアモードで計算します。",
        none: "未指定",
        selected: "選択中",
        clear: "この親を未指定に戻す",
        close: "閉じる",
      },
      loading: "予測中…",
      button: "色柄を予測する",
    },
    parentResult: {
      title: "予測結果",
      mode: "モード",
      sire: "父猫",
      dam: "母猫",
      female: "♀ メス",
      male: "♂ オス",
      totalApprox: "合計 約",
      noPhenotype: "該当する表現型がありません。",
      showDetails: "詳細を見る",
      remaining: "残り",
      close: "閉じる",
      geneticsTitle: "遺伝子情報",
      geneticsDescription:
        "座位（A / B / D…）をタップ／ホバーすると遺伝子座の解説が出ます。",
      openedLoci: "展開した座位",
      closedLoci: "固定した座位",
      otherLoci: "その他の座位",
      unmatchedProbability: "未分類の確率",
      genotypeCount: "遺伝子型",
      none: "なし",
      assumptions: "前提条件:",
      carrierScenarioTitle: "全キャリア探索シナリオ (参考・通常結果とは分離)",
      basis: "根拠",
      priorApplied: "事前確率あり",
      conditional: "条件付き",
      newCoats: "新規に出現する色柄",
    },
    targetForm: {
      registrationTitle: "登録猫の色柄",
      name: "登録名",
      namePlaceholder: "例: 青系の母猫",
      coat: "色柄",
      coatPlaceholder: "例: Blue / ブルー",
      addCoat: "＋ 色柄追加",
      additionalCoat: "追加色柄",
      breedPlaceholder: "例: British Shorthair / ブリティッシュショートヘア",
      carriers: "確認済み因子 (任意)",
      carriersLabel: "確認済み因子",
      carriersPlaceholder: "例: B:B/b, D:D/d",
      addCandidate: "猫を登録する",
      savedTitle: "登録した猫",
      savedEmpty:
        "父猫・母猫の色柄を登録すると、目標色柄に合う組み合わせを探せます。",
      sireGroup: "父猫",
      damGroup: "母猫",
      emptyGroup: "まだ登録されていません。",
      targetTitle: "目標色柄の選択",
      targetCoat: "目標色柄",
      targetPlaceholder: "例: Lilac / ライラック",
      targetSex: "子猫の性別 (任意)",
      loading: "検索中…",
      button: "組み合わせを探す",
      ranking: "候補ペア",
      targetSummary: "目標",
      noCategoryCandidates: "この条件の候補はありません。",
      matchLabel: "組み合わせ",
      productionCondition: "産出条件",
      confirmedProbability: "確定確率",
      conditionalMaxProbability: "条件付き最大確率",
      establishmentConditions: "成立条件",
      confirmationNeeded: "確認が必要な条件",
      noConfirmationNeeded: "追加確認なしで評価できます。",
      recommendedTests: "推奨検査",
      noRecommendedTests: "現時点で追加検査の提案はありません。",
      targetPossibleCoats: "目標色柄として生まれる内訳",
      noTargetCoats: "目標色柄として表示できる内訳がありません。",
      otherPossibleCoats: "目標色柄以外に生まれる可能性のある色柄",
      noOtherCoats: "現在の計算範囲では表示できる色柄がありません。",
      locus: "座位",
      targetCondition: "目標条件",
      sireSide: "父猫側",
      damSide: "母猫側",
      basis: "根拠",
      noCandidateMessage:
        "現在の登録情報では、目標色柄の成立条件を満たす組み合わせ候補を確認できません。",
      targetConditions: "目標色柄に必要な主な条件",
      uncheckedConditions: "現在確認できない条件",
      recommendedChecks: "確認するとよい項目",
      complexScopeNote:
        "ゴールデン / ワイドバンド / CORIN系は品種・系統で扱いが複雑なため、現在の対応範囲では登録情報と既存ルールに基づく確認結果として表示します。",
      categories: {
        confirmed: "条件無し",
        conditional: "条件付き",
        difficult: "判定保留",
        unavailable: "該当ペアなし",
      },
      categoryDescriptions: {
        confirmed: "表現型からのみ推定できるカラー",
        conditional:
          "父母どちらかに隠れキャリアがいると仮定すると推定できるカラー",
      },
    },
    kittenForm: {
      sectionTitle: "親猫と産子実績",
      sireCoat: "父猫の色柄",
      damCoat: "母猫の色柄",
      sirePlaceholder: "例: Blue / ブルー",
      damPlaceholder: "例: Red Tabby / レッドタビー",
      breedPlaceholder: "例: British Shorthair / ブリティッシュショートヘア",
      kittenSection: "生まれた子猫",
      addKitten: "＋ 子猫を追加",
      kittenName: "子猫名",
      kittenNamePlaceholder: "任意",
      kittenCoat: "子猫の色柄",
      kittenCoatPlaceholder: "例: Blue Patched Tabby / ブルーパッチドタビー",
      loading: "推定中…",
      button: "隠れキャリアを推定する",
      resultTitle: "推定結果",
      candidateCount: "候補",
      support: "支持",
      confirmed: "確定",
      conditional: "条件付き確定",
      inferred: "推定",
      unconfirmed: "未確認",
      confirmedEmpty: "確定できる因子はありません。",
      conditionalEmpty: "条件付きで確定できる因子はありません。",
      inferredEmpty: "推定できる因子はありません。",
      unconfirmedEmpty: "未確認として残る因子はありません。",
      warnings: "警告",
      recommendedTests: "推奨検査",
    },
  },
  en: {
    app: {
      name: "Cat Coat Planner",
      subtitle: "Kitten coat color & pattern simulator",
      languageLabel: "Language",
      japanese: "日本語",
      english: "English",
    },
    feedback: {
      trigger: "Send feedback",
      title: "Feedback",
      description: "Share feedback or requests (up to ",
      descriptionSuffix: " characters).",
      placeholder: "What did you notice? What should be improved?",
      error: "Could not send feedback. Please try again later.",
      sent: "Sent. Thank you!",
      cancel: "Cancel",
      sending: "Sending...",
      send: "Send",
    },
    tabs: {
      parent: {
        title: "Forecast from parent coats",
        description:
          "Select the sire and dam coats to estimate possible kitten coat outcomes.",
      },
      target: {
        title: "Find matches for a target coat",
        description:
          "Choose a desired kitten coat and explore possible parent combinations.",
      },
      kitten: {
        title: "Refine with actual kitten coats",
        description:
          "Use real kitten coat outcomes to infer hidden carrier candidates in the sire and dam.",
      },
    },
    onboarding: {
      helpButton: "Guide",
      progress: "{{current}} / {{total}}",
      next: "Next",
      previous: "Back",
      done: "Done",
      skip: "Skip",
      skipTour: "Skip tutorial",
      close: "Close",
      steps: {
        tabs: {
          title: "Switch tabs by workflow",
          description:
            "Use one workspace for forecasting, target-coat search, and litter-based carrier inference.",
        },
        parent: {
          title: "Start with the sire and dam",
          description:
            "Enter both parent coats to estimate the kitten coats and expected ratios.",
        },
        carriers: {
          title: "Add only confirmed factors",
          description:
            "Use these settings for tested or evidence-backed factors. Inferred carriers are checked separately in Kitten Coats.",
        },
        targetTab: {
          title: "Move to target-coat search",
          description:
            "When the desired kitten coat is already decided, use Target Coat to look for pairings.",
        },
        target: {
          title: "Choose the target coat first",
          description:
            "Select the target coat and sex, then compare registered sire and dam combinations.",
        },
        kittenTab: {
          title: "Review real litter outcomes",
          description:
            "After kittens are born, use Kitten Coats to narrow hidden carrier candidates.",
        },
        kitten: {
          title: "Infer carriers from the litter",
          description:
            "Enter the parent and kitten coats to find inferred carriers that can guide future pairings.",
        },
        help: {
          title: "Open this guide anytime",
          description:
            "Use this button whenever you want to replay the tutorial.",
        },
      },
    },
    common: {
      breed: "Breed (optional)",
      sex: "Sex",
      female: "♀ Female",
      male: "♂ Male",
      femaleCandidate: "♀ Dam candidate",
      maleCandidate: "♂ Sire candidate",
      any: "Any",
      delete: "Remove",
      edit: "Edit",
      remove: "Remove",
      cancel: "Cancel",
      update: "Save Changes",
      recent: "Recent selections",
      femaleOnly: "♀ Female only",
      geneticsAffects: "Affects genetics",
    },
    parentForm: {
      sireCoat: "Sire coat",
      damCoat: "Dam coat",
      sirePlaceholder: "e.g. Silver Tabby",
      damPlaceholder: "e.g. Brown Tabby",
      breedPlaceholder: "e.g. Abyssinian",
      mode: "Calculation mode",
      modes: {
        normal: "Normal",
        explicitCarrier: "Explicit carriers",
        carrierExploration: "Carrier exploration",
      },
      carrierHelp:
        "Enter hidden carriers as comma-separated locus:genotype values (e.g.",
      sireCarriers: "Sire carriers",
      damCarriers: "Dam carriers",
      carrierSelector: {
        buttonLabel: "Genetic settings",
        configured: "Set",
        sireButton: "Open sire genetic settings",
        damButton: "Open dam genetic settings",
        sireTitle: "Sire genetic settings",
        damTitle: "Dam genetic settings",
        description:
          "Set only confirmed loci. Unspecified loci stay in the normal calculation.",
        modeNote:
          "Selecting any locus uses explicit carrier mode for the forecast.",
        none: "Unspecified",
        selected: "Selected",
        clear: "Reset this parent",
        close: "Close",
      },
      loading: "Predicting...",
      button: "Predict Coat Colors",
    },
    parentResult: {
      title: "Forecast",
      mode: "Mode",
      sire: "Sire",
      dam: "Dam",
      female: "♀ Female",
      male: "♂ Male",
      totalApprox: "Total approx. ",
      noPhenotype: "No matching phenotype.",
      showDetails: "Show details",
      remaining: "more",
      close: "Close",
      geneticsTitle: "Genetic details",
      geneticsDescription:
        "Tap or hover a locus (A / B / D...) to see its explanation.",
      openedLoci: "Expanded loci",
      closedLoci: "Fixed loci",
      otherLoci: "Other loci",
      unmatchedProbability: "Unmatched probability",
      genotypeCount: "genotypes",
      none: "None",
      assumptions: "Assumptions:",
      carrierScenarioTitle:
        "Carrier exploration scenarios (reference, separated from normal results)",
      basis: "Basis",
      priorApplied: "prior applied",
      conditional: "conditional",
      newCoats: "Newly possible coats",
    },
    targetForm: {
      registrationTitle: "Registered cats",
      name: "Name",
      namePlaceholder: "e.g. Blue dam",
      coat: "Coat",
      coatPlaceholder: "e.g. Blue / Chocolate",
      addCoat: "+ Add Coat",
      additionalCoat: "Additional coat",
      breedPlaceholder: "e.g. British Shorthair",
      carriers: "Confirmed carriers (optional)",
      carriersLabel: "Confirmed carriers",
      carriersPlaceholder: "e.g. B:B/b, D:D/d",
      addCandidate: "Register Cat",
      savedTitle: "Registered cats",
      savedEmpty:
        "Register sire and dam coat colors to find pairings for the target coat.",
      sireGroup: "Sires",
      damGroup: "Dams",
      emptyGroup: "No cats registered yet.",
      targetTitle: "Target coat",
      targetCoat: "Target coat",
      targetPlaceholder: "e.g. Lilac / Cinnamon Golden Tabby",
      targetSex: "Kitten sex (optional)",
      loading: "Searching...",
      button: "Find Pairings",
      ranking: "Candidate pairs",
      targetSummary: "Target",
      noCategoryCandidates: "No pairs in this group.",
      matchLabel: "Match",
      productionCondition: "Production condition",
      confirmedProbability: "Confirmed probability",
      conditionalMaxProbability: "Conditional max probability",
      establishmentConditions: "Required conditions",
      confirmationNeeded: "Needs confirmation",
      noConfirmationNeeded: "Can be evaluated without extra confirmation.",
      recommendedTests: "Recommended tests",
      noRecommendedTests: "No additional tests are suggested right now.",
      targetPossibleCoats: "Target coat outcomes",
      noTargetCoats: "No target coat outcome is available.",
      otherPossibleCoats: "Other possible kitten coats",
      noOtherCoats: "No coats are available in the current calculation range.",
      locus: "Locus",
      targetCondition: "Target condition",
      sireSide: "Sire side",
      damSide: "Dam side",
      basis: "Basis",
      noCandidateMessage:
        "No registered combination currently satisfies the target coat conditions.",
      targetConditions: "Main conditions for the target coat",
      uncheckedConditions: "Conditions not confirmed yet",
      recommendedChecks: "Useful checks",
      complexScopeNote:
        "Golden, wideband, and CORIN-related coats vary by breed and line, so this view shows what can be checked from the registered data and current rules.",
      categories: {
        confirmed: "No conditions",
        conditional: "Conditional",
        difficult: "Needs review",
        unavailable: "No matching pair",
      },
      categoryDescriptions: {
        confirmed: "Coats inferred from visible phenotype only.",
        conditional:
          "Coats inferred when either parent is assumed to carry a hidden factor.",
      },
    },
    kittenForm: {
      sectionTitle: "Parents and litter record",
      sireCoat: "Sire coat",
      damCoat: "Dam coat",
      sirePlaceholder: "e.g. Blue",
      damPlaceholder: "e.g. Red Tabby",
      breedPlaceholder: "e.g. British Shorthair",
      kittenSection: "Born kittens",
      addKitten: "+ Add Kitten",
      kittenName: "Kitten name",
      kittenNamePlaceholder: "Optional",
      kittenCoat: "Kitten coat",
      kittenCoatPlaceholder: "e.g. Blue Patched Tabby",
      loading: "Inferring...",
      button: "Infer Hidden Carriers",
      resultTitle: "Carrier inference",
      candidateCount: "candidates",
      support: "support",
      confirmed: "Confirmed",
      conditional: "Conditional",
      inferred: "Inferred",
      unconfirmed: "Unconfirmed",
      confirmedEmpty: "No confirmed factors.",
      conditionalEmpty: "No conditionally confirmed factors.",
      inferredEmpty: "No inferred factors.",
      unconfirmedEmpty: "No unconfirmed factors remain.",
      warnings: "Warnings",
      recommendedTests: "Recommended tests",
    },
  },
} as const;
