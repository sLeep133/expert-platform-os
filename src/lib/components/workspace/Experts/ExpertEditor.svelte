<script lang="ts">
import { goto } from '$app/navigation';
import { getContext } from 'svelte';
import { toast } from 'svelte-sonner';

import Spinner from '$lib/components/common/Spinner.svelte';
import Textarea from '$lib/components/common/Textarea.svelte';
import type { Expert, ExpertForm } from '$lib/apis/experts';

const i18n = getContext('i18n');

export let expert: Expert | null = null;
export let clone = false;
export let onSubmit: (expert: ExpertForm) => Promise<void>;

let name = '';
let description = '';
let avatar = '';
let tags = '';
let visibility = 'private';

let role = '';
let tone = '';
let style = '';
let constraints = '';

let principles = '';
let workflows = '';
let outputPreferences = '';

let model = '';
let provider = '';
let contextBudget = '';
let toolPolicy = 'safe';
let collaborationMode = 'solo';

let spaces = '';
let pinnedPages = '';
let sourceFilters = '';
let systemPrompt = '';

let submitting = false;

const lines = (value: string) =>
value
.split('\n')
.map((item) => item.trim())
.filter(Boolean);

const csv = (value: string) =>
value
.split(',')
.map((item) => item.trim())
.filter(Boolean);

$: if (expert) {
name = clone ? `${expert.name} (Copy)` : expert.name ?? '';
description = expert.description ?? '';
avatar = expert.avatar ?? '';
tags = (expert.tags ?? []).join(', ');
visibility = clone ? 'private' : expert.visibility ?? 'private';
role = expert.persona_role ?? '';
tone = expert.persona_tone ?? '';
style = expert.persona_style ?? '';
constraints = (expert.persona_constraints ?? []).join('\n');
principles = (expert.method_principles ?? []).join('\n');
workflows = (expert.method_workflows ?? []).join('\n');
outputPreferences = (expert.method_output_preferences ?? []).join('\n');
model = expert.runtime_model ?? '';
provider = expert.runtime_provider ?? '';
contextBudget = expert.runtime_context_budget != null ? String(expert.runtime_context_budget) : '';
toolPolicy = expert.runtime_tool_policy ?? 'safe';
collaborationMode = expert.runtime_collaboration_mode ?? 'solo';
spaces = (expert.knowledge_spaces ?? []).join('\n');
pinnedPages = (expert.knowledge_pinned_pages ?? []).join('\n');
sourceFilters = (expert.knowledge_source_filters ?? []).join('\n');
systemPrompt = expert.system_prompt ?? '';
}

const submit = async () => {
if (!name.trim()) {
toast.error($i18n.t('Name is required'));
return;
}

submitting = true;
try {
await onSubmit({
name: name.trim(),
description: description.trim() || null,
avatar: avatar.trim() || null,
tags: csv(tags),
visibility,
persona: {
role: role.trim() || null,
tone: tone.trim() || null,
style: style.trim() || null,
constraints: lines(constraints)
},
method: {
principles: lines(principles),
workflows: lines(workflows),
output_preferences: lines(outputPreferences)
},
runtime: {
model: model.trim() || null,
provider: provider.trim() || null,
context_budget: contextBudget.trim() ? Number(contextBudget) : null,
tool_policy: toolPolicy,
collaboration_mode: collaborationMode
},
knowledge_view: {
spaces: lines(spaces),
pinned_pages: lines(pinnedPages),
source_filters: lines(sourceFilters)
},
system_prompt: systemPrompt.trim() || null
});
} finally {
submitting = false;
}
};
</script>

<div class="mx-auto max-w-5xl px-1 py-4 flex flex-col gap-4">
<div class="flex items-center justify-between gap-3">
<div>
<div class="text-2xl font-semibold text-gray-900 dark:text-gray-100">
{expert ? $i18n.t('Edit Expert') : $i18n.t('New Expert')}
</div>
<div class="text-sm text-gray-500 dark:text-gray-400 mt-1">
{$i18n.t('Configure persona, method, runtime and knowledge view for this expert.')}
</div>
</div>

<div class="flex items-center gap-2">
<button
class="px-3 py-2 rounded-xl text-sm border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-900 transition"
on:click={() => goto('/workspace/experts')}
>
{$i18n.t('Cancel')}
</button>
<button
class="px-3 py-2 rounded-xl text-sm bg-gray-900 text-white dark:bg-white dark:text-gray-900 hover:opacity-90 transition flex items-center gap-2"
disabled={submitting}
on:click={submit}
>
{#if submitting}
<Spinner className="size-4" />
{/if}
{$i18n.t('Save')}
</button>
</div>
</div>

<div class="grid grid-cols-1 xl:grid-cols-2 gap-4">
<div class="rounded-2xl border border-gray-100 dark:border-gray-900 p-4 bg-white dark:bg-gray-950 flex flex-col gap-3">
<div class="font-medium text-gray-900 dark:text-gray-100">{$i18n.t('Basic Info')}</div>
<input bind:value={name} class="w-full rounded-xl px-3 py-2 text-sm bg-gray-50 dark:bg-gray-900 outline-hidden" placeholder={$i18n.t('Name')} />
<input bind:value={description} class="w-full rounded-xl px-3 py-2 text-sm bg-gray-50 dark:bg-gray-900 outline-hidden" placeholder={$i18n.t('Description')} />
<input bind:value={avatar} class="w-full rounded-xl px-3 py-2 text-sm bg-gray-50 dark:bg-gray-900 outline-hidden" placeholder={$i18n.t('Avatar URL')} />
<input bind:value={tags} class="w-full rounded-xl px-3 py-2 text-sm bg-gray-50 dark:bg-gray-900 outline-hidden" placeholder={$i18n.t('Tags, separated by commas')} />
<select bind:value={visibility} class="w-full rounded-xl px-3 py-2 text-sm bg-gray-50 dark:bg-gray-900 outline-hidden">
<option value="private">private</option>
<option value="shared">shared</option>
</select>
</div>

<div class="rounded-2xl border border-gray-100 dark:border-gray-900 p-4 bg-white dark:bg-gray-950 flex flex-col gap-3">
<div class="font-medium text-gray-900 dark:text-gray-100">{$i18n.t('Persona')}</div>
<input bind:value={role} class="w-full rounded-xl px-3 py-2 text-sm bg-gray-50 dark:bg-gray-900 outline-hidden" placeholder={$i18n.t('Role')} />
<input bind:value={tone} class="w-full rounded-xl px-3 py-2 text-sm bg-gray-50 dark:bg-gray-900 outline-hidden" placeholder={$i18n.t('Tone')} />
<input bind:value={style} class="w-full rounded-xl px-3 py-2 text-sm bg-gray-50 dark:bg-gray-900 outline-hidden" placeholder={$i18n.t('Style')} />
<Textarea bind:value={constraints} rows={4} placeholder={$i18n.t('Constraints, one per line')} />
</div>

<div class="rounded-2xl border border-gray-100 dark:border-gray-900 p-4 bg-white dark:bg-gray-950 flex flex-col gap-3">
<div class="font-medium text-gray-900 dark:text-gray-100">{$i18n.t('Method')}</div>
<Textarea bind:value={principles} rows={4} placeholder={$i18n.t('Principles, one per line')} />
<Textarea bind:value={workflows} rows={4} placeholder={$i18n.t('Workflows, one per line')} />
<Textarea bind:value={outputPreferences} rows={4} placeholder={$i18n.t('Output preferences, one per line')} />
</div>

<div class="rounded-2xl border border-gray-100 dark:border-gray-900 p-4 bg-white dark:bg-gray-950 flex flex-col gap-3">
<div class="font-medium text-gray-900 dark:text-gray-100">{$i18n.t('Runtime')}</div>
<input bind:value={model} class="w-full rounded-xl px-3 py-2 text-sm bg-gray-50 dark:bg-gray-900 outline-hidden" placeholder={$i18n.t('Default model')} />
<input bind:value={provider} class="w-full rounded-xl px-3 py-2 text-sm bg-gray-50 dark:bg-gray-900 outline-hidden" placeholder={$i18n.t('Provider')} />
<input bind:value={contextBudget} class="w-full rounded-xl px-3 py-2 text-sm bg-gray-50 dark:bg-gray-900 outline-hidden" placeholder={$i18n.t('Context budget')} />
<select bind:value={toolPolicy} class="w-full rounded-xl px-3 py-2 text-sm bg-gray-50 dark:bg-gray-900 outline-hidden">
<option value="safe">safe</option>
<option value="ask">ask</option>
<option value="allow-all">allow-all</option>
</select>
<select bind:value={collaborationMode} class="w-full rounded-xl px-3 py-2 text-sm bg-gray-50 dark:bg-gray-900 outline-hidden">
<option value="solo">solo</option>
<option value="lead-assist">lead-assist</option>
<option value="generate-review">generate-review</option>
</select>
</div>

<div class="rounded-2xl border border-gray-100 dark:border-gray-900 p-4 bg-white dark:bg-gray-950 flex flex-col gap-3 xl:col-span-2">
<div class="font-medium text-gray-900 dark:text-gray-100">{$i18n.t('Knowledge View')}</div>
<div class="grid grid-cols-1 md:grid-cols-3 gap-3">
<Textarea bind:value={spaces} rows={5} placeholder={$i18n.t('Knowledge spaces, one per line')} />
<Textarea bind:value={pinnedPages} rows={5} placeholder={$i18n.t('Pinned pages, one per line')} />
<Textarea bind:value={sourceFilters} rows={5} placeholder={$i18n.t('Source filters, one per line')} />
</div>
</div>

<div class="rounded-2xl border border-gray-100 dark:border-gray-900 p-4 bg-white dark:bg-gray-950 flex flex-col gap-3 xl:col-span-2">
<div class="font-medium text-gray-900 dark:text-gray-100">{$i18n.t('System Prompt')}</div>
<Textarea bind:value={systemPrompt} rows={8} placeholder={$i18n.t('Optional composed system prompt')} />
</div>
</div>
</div>
