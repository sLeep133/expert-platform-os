<script lang="ts">
import { goto } from '$app/navigation';
import { onMount } from 'svelte';
import { toast } from 'svelte-sonner';

import Spinner from '$lib/components/common/Spinner.svelte';
import Textarea from '$lib/components/common/Textarea.svelte';
import type { Expert, ExpertForm } from '$lib/apis/experts';
import { getKnowledgeBases, getKnowledgeById } from '$lib/apis/knowledge';

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
let loadingKnowledge = false;
let loadingKnowledgePages = false;
let showAdvanced = false;

type WikiPage = {
id: string;
title: string;
source_name?: string;
summary?: string;
};

type KnowledgeOption = {
id: string;
name: string;
description?: string;
meta?: {
expert_platform?: {
compile?: {
status?: string;
};
wiki?: {
pages?: WikiPage[];
};
};
};
};

let availableKnowledge: KnowledgeOption[] = [];
let knowledgePagesBySpace: Record<string, WikiPage[]> = {};
let requestedKnowledgeDetails: string[] = [];
let selectedKnowledge: KnowledgeOption[] = [];
let selectablePinnedPages: Array<
WikiPage & {
knowledge_id: string;
knowledge_name: string;
}
> = [];

const lines = (value: string) =>
value
.split('\n')
.map((item) => item.trim())
.filter(Boolean);

const unique = (values: string[]) => Array.from(new Set(values));

const normalizedLines = (value: string) => unique(lines(value));

const csv = (value: string) =>
value
.split(',')
.map((item) => item.trim())
.filter(Boolean);

const setSpaces = (values: string[]) => {
spaces = unique(values).join('\n');
};

const setPinnedPages = (values: string[]) => {
pinnedPages = unique(values).join('\n');
};

const removePinnedPagesForSpace = (spaceId: string) => {
const pageIds = new Set((knowledgePagesBySpace[spaceId] ?? []).map((page) => page.id));
if (!pageIds.size) return;

setPinnedPages(normalizedLines(pinnedPages).filter((pageId) => !pageIds.has(pageId)));
};

const loadKnowledgeOptions = async () => {
loadingKnowledge = true;

try {
let page = 1;
let collected: KnowledgeOption[] = [];
let total = 0;

while (true) {
const res = await getKnowledgeBases(localStorage.token, page);
const items = res?.items ?? [];
total = res?.total ?? collected.length + items.length;
collected = [...collected, ...items];

if (items.length === 0 || collected.length >= total) {
break;
}

page += 1;
}

availableKnowledge = collected;
} catch (e) {
toast.error(`${e}`);
} finally {
loadingKnowledge = false;
}
};

const loadKnowledgeDetail = async (spaceId: string) => {
if (!spaceId || requestedKnowledgeDetails.includes(spaceId)) {
return;
}

requestedKnowledgeDetails = [...requestedKnowledgeDetails, spaceId];
loadingKnowledgePages = true;

try {
const detail = await getKnowledgeById(localStorage.token, spaceId);
knowledgePagesBySpace = {
...knowledgePagesBySpace,
[spaceId]: detail?.meta?.expert_platform?.wiki?.pages ?? []
};
} catch (e) {
toast.error(`${e}`);
} finally {
loadingKnowledgePages = false;
}
};

const hydrateSelectedKnowledgePages = async (spaceIds: string[]) => {
for (const spaceId of spaceIds) {
if (!knowledgePagesBySpace[spaceId]) {
await loadKnowledgeDetail(spaceId);
}
}
};

const toggleKnowledgeSpace = async (spaceId: string) => {
const current = new Set(normalizedLines(spaces));

if (current.has(spaceId)) {
current.delete(spaceId);
setSpaces(Array.from(current));
removePinnedPagesForSpace(spaceId);
return;
}

current.add(spaceId);
setSpaces(Array.from(current));
await loadKnowledgeDetail(spaceId);
};

const togglePinnedPage = (pageId: string) => {
const current = new Set(normalizedLines(pinnedPages));

if (current.has(pageId)) {
current.delete(pageId);
} else {
current.add(pageId);
}

setPinnedPages(Array.from(current));
};

const getSelectedSpaces = () => normalizedLines(spaces);
const getSelectedPinnedPages = () => normalizedLines(pinnedPages);

$: selectedKnowledge = availableKnowledge.filter((item) => getSelectedSpaces().includes(item.id));

$: selectablePinnedPages = selectedKnowledge.flatMap((item) =>
(knowledgePagesBySpace[item.id] ?? []).map((page) => ({
...page,
knowledge_id: item.id,
knowledge_name: item.name
}))
);

$: if (availableKnowledge.length > 0) {
void hydrateSelectedKnowledgePages(getSelectedSpaces());
}

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

onMount(async () => {
await loadKnowledgeOptions();
});

const submit = async () => {
if (!name.trim()) {
toast.error('请输入专家名称');
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
{expert ? '编辑专家' : '新建专家'}
</div>
<div class="text-sm text-gray-500 dark:text-gray-400 mt-1">
只填名称并关联知识空间就能先用起来。
</div>
</div>

<div class="flex items-center gap-2">
<button
class="px-3 py-2 rounded-xl text-sm border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-900 transition"
on:click={() => goto('/workspace/experts')}
>
取消
</button>
<button
class="px-3 py-2 rounded-xl text-sm bg-gray-900 text-white dark:bg-white dark:text-gray-900 hover:opacity-90 transition flex items-center gap-2"
disabled={submitting}
on:click={submit}
>
{#if submitting}
<Spinner className="size-4" />
{/if}
保存
</button>
</div>
</div>

<div class="grid grid-cols-1 gap-4">
<div class="rounded-2xl border border-gray-100 dark:border-gray-900 p-4 bg-white dark:bg-gray-950 flex flex-col gap-3">
<div class="font-medium text-gray-900 dark:text-gray-100">基础信息</div>
<input bind:value={name} class="w-full rounded-xl px-3 py-2 text-sm bg-gray-50 dark:bg-gray-900 outline-hidden" placeholder="专家名称" />
<div class="text-xs text-gray-500 dark:text-gray-400">
默认会按你选择的知识空间回答，其他角色、模型、提示词都可以稍后再补。
</div>
</div>

<div class="rounded-2xl border border-gray-100 dark:border-gray-900 p-4 bg-white dark:bg-gray-950 flex flex-col gap-3">
<div class="flex items-center justify-between gap-3">
<div>
<div class="font-medium text-gray-900 dark:text-gray-100">知识关联</div>
<div class="mt-1 text-xs text-gray-500 dark:text-gray-400">
先选知识空间；如果已经编译出 Wiki 页面，再按需勾选重点页面。
</div>
</div>
<div class="text-xs text-gray-500 dark:text-gray-400">
已选知识空间 {getSelectedSpaces().length} 个
</div>
</div>
{#if loadingKnowledge}
<div class="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
<Spinner className="size-4" />
<span>正在加载知识空间</span>
</div>
{:else if availableKnowledge.length > 0}
<div class="rounded-2xl border border-gray-100 dark:border-gray-900 bg-gray-50/70 dark:bg-gray-900/40 p-3">
<div class="text-sm font-medium text-gray-900 dark:text-gray-100">
可选知识空间
</div>
<div class="mt-3 grid grid-cols-1 md:grid-cols-2 gap-2">
{#each availableKnowledge as item}
<button
type="button"
class="w-full text-left rounded-xl border px-3 py-3 transition {getSelectedSpaces().includes(item.id)
? 'border-gray-900 bg-white dark:border-gray-100 dark:bg-gray-950'
: 'border-gray-200 bg-white/70 hover:bg-white dark:border-gray-800 dark:bg-gray-950/60 dark:hover:bg-gray-950'}"
on:click={() => toggleKnowledgeSpace(item.id)}
>
<div class="flex items-start justify-between gap-3">
<div>
<div class="text-sm font-medium text-gray-900 dark:text-gray-100">{item.name}</div>
{#if item.description}
<div class="mt-1 text-xs text-gray-500 dark:text-gray-400 line-clamp-2">
{item.description}
</div>
{/if}
</div>
<div class="text-[11px] px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-900 text-gray-600 dark:text-gray-300">
{item.meta?.expert_platform?.compile?.status ?? 'idle'}
</div>
</div>
</button>
{/each}
</div>
</div>

{#if getSelectedSpaces().length > 0}
<div class="rounded-2xl border border-gray-100 dark:border-gray-900 bg-gray-50/70 dark:bg-gray-900/40 p-3">
<div class="flex items-center justify-between gap-3">
<div class="text-sm font-medium text-gray-900 dark:text-gray-100">
重点 Wiki 页面（可选）
</div>
{#if loadingKnowledgePages}
<div class="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
<Spinner className="size-3.5" />
<span>正在加载页面</span>
</div>
{/if}
</div>

{#if selectablePinnedPages.length > 0}
<div class="mt-3 grid grid-cols-1 md:grid-cols-2 gap-2">
{#each selectablePinnedPages as page}
<button
type="button"
class="w-full text-left rounded-xl border px-3 py-3 transition {getSelectedPinnedPages().includes(page.id)
? 'border-gray-900 bg-white dark:border-gray-100 dark:bg-gray-950'
: 'border-gray-200 bg-white/70 hover:bg-white dark:border-gray-800 dark:bg-gray-950/60 dark:hover:bg-gray-950'}"
on:click={() => togglePinnedPage(page.id)}
>
<div class="text-xs text-gray-500 dark:text-gray-400">{page.knowledge_name}</div>
<div class="mt-1 text-sm font-medium text-gray-900 dark:text-gray-100">{page.title}</div>
{#if page.source_name}
<div class="mt-1 text-xs text-gray-500 dark:text-gray-400">{page.source_name}</div>
{/if}
{#if page.summary}
<div class="mt-2 text-xs text-gray-600 dark:text-gray-300 line-clamp-2">{page.summary}</div>
{/if}
</button>
{/each}
</div>
{:else}
<div class="mt-3 text-xs text-gray-500 dark:text-gray-400">
已选知识空间还没有可选页面，直接保存也可以使用。
</div>
{/if}
</div>
{/if}
{:else}
<div class="rounded-xl border border-dashed border-gray-200 dark:border-gray-800 px-3 py-4 text-sm text-gray-500 dark:text-gray-400">
暂无可用知识空间，请先去知识库里创建并编译 Wiki。
</div>
{/if}

</div>

<details class="rounded-2xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950" bind:open={showAdvanced}>
<summary class="cursor-pointer list-none px-4 py-3 flex items-center justify-between gap-3">
<div>
<div class="font-medium text-gray-900 dark:text-gray-100">高级设置</div>
<div class="mt-1 text-xs text-gray-500 dark:text-gray-400">
说明、标签、可见性、角色、运行时和系统提示词都放在这里，不填也能先用。
</div>
</div>
<div class="text-xs text-gray-500 dark:text-gray-400">
{showAdvanced ? '收起' : '展开'}
</div>
</summary>

<div class="px-4 pb-4 grid grid-cols-1 xl:grid-cols-2 gap-4">
<div class="rounded-2xl border border-gray-100 dark:border-gray-900 p-4 bg-gray-50/40 dark:bg-gray-900/30 flex flex-col gap-3">
<div class="font-medium text-gray-900 dark:text-gray-100">补充信息</div>
<input bind:value={description} class="w-full rounded-xl px-3 py-2 text-sm bg-white dark:bg-gray-950 outline-hidden" placeholder="专家说明（可选）" />
<input bind:value={avatar} class="w-full rounded-xl px-3 py-2 text-sm bg-white dark:bg-gray-950 outline-hidden" placeholder="头像链接（可选）" />
<input bind:value={tags} class="w-full rounded-xl px-3 py-2 text-sm bg-white dark:bg-gray-950 outline-hidden" placeholder="标签，多个用逗号分隔" />
<select bind:value={visibility} class="w-full rounded-xl px-3 py-2 text-sm bg-white dark:bg-gray-950 outline-hidden">
<option value="private">私有</option>
<option value="shared">共享</option>
</select>
</div>

<div class="rounded-2xl border border-gray-100 dark:border-gray-900 p-4 bg-gray-50/40 dark:bg-gray-900/30 flex flex-col gap-3">
<div class="font-medium text-gray-900 dark:text-gray-100">角色设定</div>
<input bind:value={role} class="w-full rounded-xl px-3 py-2 text-sm bg-white dark:bg-gray-950 outline-hidden" placeholder="角色" />
<input bind:value={tone} class="w-full rounded-xl px-3 py-2 text-sm bg-white dark:bg-gray-950 outline-hidden" placeholder="语气" />
<input bind:value={style} class="w-full rounded-xl px-3 py-2 text-sm bg-white dark:bg-gray-950 outline-hidden" placeholder="表达风格" />
<Textarea bind:value={constraints} rows={4} placeholder="约束条件，一行一个" />
</div>

<div class="rounded-2xl border border-gray-100 dark:border-gray-900 p-4 bg-gray-50/40 dark:bg-gray-900/30 flex flex-col gap-3">
<div class="font-medium text-gray-900 dark:text-gray-100">运行时</div>
<input bind:value={model} class="w-full rounded-xl px-3 py-2 text-sm bg-white dark:bg-gray-950 outline-hidden" placeholder="默认模型（可选）" />
<input bind:value={provider} class="w-full rounded-xl px-3 py-2 text-sm bg-white dark:bg-gray-950 outline-hidden" placeholder="提供方（可选）" />
<input bind:value={contextBudget} class="w-full rounded-xl px-3 py-2 text-sm bg-white dark:bg-gray-950 outline-hidden" placeholder="上下文预算（可选）" />
<select bind:value={toolPolicy} class="w-full rounded-xl px-3 py-2 text-sm bg-white dark:bg-gray-950 outline-hidden">
<option value="safe">safe</option>
<option value="ask">ask</option>
<option value="allow-all">allow-all</option>
</select>
<select bind:value={collaborationMode} class="w-full rounded-xl px-3 py-2 text-sm bg-white dark:bg-gray-950 outline-hidden">
<option value="solo">solo</option>
<option value="lead-assist">lead-assist</option>
<option value="generate-review">generate-review</option>
</select>
</div>

<div class="rounded-2xl border border-gray-100 dark:border-gray-900 p-4 bg-gray-50/40 dark:bg-gray-900/30 flex flex-col gap-3">
<div class="font-medium text-gray-900 dark:text-gray-100">方法</div>
<Textarea bind:value={principles} rows={4} placeholder="原则，一行一个" />
<Textarea bind:value={workflows} rows={4} placeholder="工作流，一行一个" />
<Textarea bind:value={outputPreferences} rows={4} placeholder="输出偏好，一行一个" />
</div>

<div class="rounded-2xl border border-gray-100 dark:border-gray-900 p-4 bg-gray-50/40 dark:bg-gray-900/30 flex flex-col gap-3">
<div class="font-medium text-gray-900 dark:text-gray-100">系统提示词</div>
<Textarea bind:value={systemPrompt} rows={8} placeholder="可选的系统提示词" />
</div>

<div class="rounded-2xl border border-gray-100 dark:border-gray-900 p-4 bg-gray-50/40 dark:bg-gray-900/30 flex flex-col gap-3 xl:col-span-2">
<div class="font-medium text-gray-900 dark:text-gray-100">高级知识设置</div>
<div class="text-xs text-gray-500 dark:text-gray-400">
通常不需要手填，只有你明确知道这些 ID 或过滤条件时再使用。
</div>
<div class="grid grid-cols-1 md:grid-cols-3 gap-3">
<Textarea bind:value={spaces} rows={4} placeholder="知识空间 ID（高级模式，一行一个）" />
<Textarea bind:value={pinnedPages} rows={4} placeholder="固定页面 ID（高级模式，一行一个）" />
<Textarea bind:value={sourceFilters} rows={4} placeholder="来源过滤条件（高级模式，一行一个）" />
</div>
</div>
</div>
</details>
</div>
</div>
