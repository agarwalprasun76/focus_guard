import { requestJson } from "./client";

// ── Types ─────────────────────────────────────────────────────────

export type EnforcementMode = "tracking" | "advisory" | "enforcing";

export type EnforcementResponse = {
  enforcement_mode: EnforcementMode;
  password_required?: boolean;
};

export type SetEnforcementInput = {
  mode: EnforcementMode;
  password?: string;
};

export type SetEnforcementResponse = {
  updated: boolean;
  mode: EnforcementMode;
};

export type BudgetsResponse = {
  master_budget?: {
    daily_seconds?: number;
    remaining_seconds?: number;
  };
  classification_budgets?: Record<
    string,
    { daily_seconds: number; remaining_seconds?: number }
  >;
  domain_budgets?: Record<
    string,
    { daily_seconds: number; remaining_seconds?: number }
  >;
  distraction?: {
    budget_seconds?: number;
    used_seconds?: number;
    remaining_seconds?: number;
    percent_used?: number;
  };
};

export type UpdateMasterBudgetInput = {
  daily_seconds: number;
};

export type DomainEntry = {
  domain: string;
  category?: string;
  status?: string;
  budget_seconds?: number | null;
  usage_seconds?: number;
  whitelisted?: boolean;
  blocked?: boolean;
};

export type DomainsOverviewResponse = {
  domains?: DomainEntry[];
  categories?: string[];
};

export type SetDomainCategoryInput = {
  domain: string;
  category: string;
};

export type WhitelistDomainInput = {
  domain: string;
  action: "add" | "remove";
};

export type SetDomainBudgetInput = {
  domain: string;
  daily_seconds: number;
};

// ── API functions ─────────────────────────────────────────────────

export function getEnforcement(): Promise<EnforcementResponse> {
  return requestJson<EnforcementResponse>("/settings/enforcement");
}

export function setEnforcement(input: SetEnforcementInput): Promise<SetEnforcementResponse> {
  return requestJson<SetEnforcementResponse>("/settings/enforcement", {
    method: "POST",
    body: input,
  });
}

export function getBudgets(): Promise<BudgetsResponse> {
  return requestJson<BudgetsResponse>("/settings/budgets");
}

export function updateMasterBudget(input: UpdateMasterBudgetInput): Promise<Record<string, unknown>> {
  return requestJson("/settings/budgets/master", {
    method: "POST",
    body: input,
  });
}

export function updateClassificationBudget(
  classification: string,
  daily_seconds: number,
): Promise<Record<string, unknown>> {
  return requestJson("/settings/budgets/classification", {
    method: "POST",
    body: { classification, daily_seconds },
  });
}

export function getDomains(): Promise<DomainsOverviewResponse> {
  return requestJson<DomainsOverviewResponse>("/settings/domains");
}

export function setDomainCategory(input: SetDomainCategoryInput): Promise<Record<string, unknown>> {
  return requestJson("/settings/domains/category", {
    method: "POST",
    body: input,
  });
}

export function whitelistDomain(input: WhitelistDomainInput): Promise<Record<string, unknown>> {
  return requestJson("/settings/domains/whitelist", {
    method: "POST",
    body: input,
  });
}

export function setDomainBudget(input: SetDomainBudgetInput): Promise<Record<string, unknown>> {
  return requestJson("/settings/domains/budget", {
    method: "POST",
    body: input,
  });
}
