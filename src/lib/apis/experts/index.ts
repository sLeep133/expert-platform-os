import { WEBUI_API_BASE_URL } from '$lib/constants';

export type PersonaForm = {
role?: string | null;
tone?: string | null;
style?: string | null;
constraints?: string[];
};

export type MethodForm = {
principles?: string[];
workflows?: string[];
output_preferences?: string[];
};

export type RuntimeForm = {
model?: string | null;
provider?: string | null;
context_budget?: number | null;
tool_policy?: string;
collaboration_mode?: string;
};

export type KnowledgeViewForm = {
spaces?: string[];
pinned_pages?: string[];
source_filters?: string[];
};

export type ExpertForm = {
name: string;
description?: string | null;
avatar?: string | null;
tags?: string[];
visibility?: string;
persona?: PersonaForm | null;
method?: MethodForm | null;
runtime?: RuntimeForm | null;
knowledge_view?: KnowledgeViewForm | null;
system_prompt?: string | null;
};

export type Expert = {
id: string;
user_id: string;
name: string;
description?: string | null;
avatar?: string | null;
tags: string[];
visibility: string;
persona_role?: string | null;
persona_tone?: string | null;
persona_style?: string | null;
persona_constraints: string[];
method_principles: string[];
method_workflows: string[];
method_output_preferences: string[];
runtime_model?: string | null;
runtime_provider?: string | null;
runtime_context_budget?: number | null;
runtime_tool_policy: string;
runtime_collaboration_mode: string;
knowledge_spaces: string[];
knowledge_pinned_pages: string[];
knowledge_source_filters: string[];
system_prompt?: string | null;
created_at: number;
updated_at: number;
user?: {
id: string;
name: string;
email: string;
} | null;
};

const parseJson = async (res: Response) => {
if (!res.ok) throw await res.json();
return res.json();
};

const getErrorMessage = (err: any) => err?.detail ?? err;

export const getExperts = async (token: string = ''): Promise<Expert[]> => {
let error = null;

const res = await fetch(`${WEBUI_API_BASE_URL}/experts/`, {
method: 'GET',
headers: {
Accept: 'application/json',
'Content-Type': 'application/json',
authorization: `Bearer ${token}`
}
})
.then(parseJson)
.catch((err) => {
error = getErrorMessage(err);
console.error(err);
return null;
});

if (error) throw error;
return res ?? [];
};

export const getExpertById = async (token: string, id: string): Promise<Expert> => {
let error = null;

const res = await fetch(`${WEBUI_API_BASE_URL}/experts/${id}`, {
method: 'GET',
headers: {
Accept: 'application/json',
'Content-Type': 'application/json',
authorization: `Bearer ${token}`
}
})
.then(parseJson)
.catch((err) => {
error = getErrorMessage(err);
console.error(err);
return null;
});

if (error) throw error;
return res;
};

export const createExpert = async (token: string, expert: ExpertForm): Promise<Expert> => {
let error = null;

const res = await fetch(`${WEBUI_API_BASE_URL}/experts/create`, {
method: 'POST',
headers: {
Accept: 'application/json',
'Content-Type': 'application/json',
authorization: `Bearer ${token}`
},
body: JSON.stringify(expert)
})
.then(parseJson)
.catch((err) => {
error = getErrorMessage(err);
console.error(err);
return null;
});

if (error) throw error;
return res;
};

export const updateExpertById = async (
token: string,
id: string,
expert: ExpertForm
): Promise<Expert> => {
let error = null;

const res = await fetch(`${WEBUI_API_BASE_URL}/experts/${id}/update`, {
method: 'POST',
headers: {
Accept: 'application/json',
'Content-Type': 'application/json',
authorization: `Bearer ${token}`
},
body: JSON.stringify(expert)
})
.then(parseJson)
.catch((err) => {
error = getErrorMessage(err);
console.error(err);
return null;
});

if (error) throw error;
return res;
};

export const deleteExpertById = async (token: string, id: string): Promise<boolean> => {
let error = null;

const res = await fetch(`${WEBUI_API_BASE_URL}/experts/${id}/delete`, {
method: 'DELETE',
headers: {
Accept: 'application/json',
'Content-Type': 'application/json',
authorization: `Bearer ${token}`
}
})
.then(parseJson)
.catch((err) => {
error = getErrorMessage(err);
console.error(err);
return null;
});

if (error) throw error;
return res;
};

export const duplicateExpertById = async (token: string, id: string): Promise<Expert> => {
let error = null;

const res = await fetch(`${WEBUI_API_BASE_URL}/experts/${id}/duplicate`, {
method: 'POST',
headers: {
Accept: 'application/json',
'Content-Type': 'application/json',
authorization: `Bearer ${token}`
}
})
.then(parseJson)
.catch((err) => {
error = getErrorMessage(err);
console.error(err);
return null;
});

if (error) throw error;
return res;
};
