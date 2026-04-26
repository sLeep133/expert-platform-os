<script lang="ts">
import { onMount } from 'svelte';
import { toast } from 'svelte-sonner';
import Spinner from '$lib/components/common/Spinner.svelte';
import ArrowUpTray from '$lib/components/icons/ArrowUpTray.svelte';
import Folder from '$lib/components/icons/Folder.svelte';
import Document from '$lib/components/icons/Document.svelte';
import CheckCircle from '$lib/components/icons/CheckCircle.svelte';
import XMark from '$lib/components/icons/XMark.svelte';
import Bolt from '$lib/components/icons/Bolt.svelte';
import Refresh from '$lib/components/icons/Refresh.svelte';

import {
getExpertWikiStatus,
listExpertWikiPages,
readExpertWikiPage,
uploadToExpertWiki,
compileExpertWiki,
getExpertWikiHealth,
triggerExpertWikiHealthCheck,
type WikiStatus,
type WikiPage,
type WikiHealthReport
} from '$lib/apis/experts';

export let expertId: string;

let loading = true;
let compiling = false;
let uploading = false;
let checking = false;

let wikiStatus: WikiStatus | null = null;
let wikiPages: WikiPage[] = [];
let healthReport: WikiHealthReport | null = null;
let selectedPage: WikiPage | null = null;
let pageContent = '';

let activeTab: 'files' | 'pages' | 'health' = 'files';
let fileInput: HTMLInputElement;

const loadWikiStatus = async () => {
try {
wikiStatus = await getExpertWikiStatus(localStorage.token, expertId);
} catch (e) {
toast.error(`${e}`);
}
};

const loadWikiPages = async () => {
try {
const res = await listExpertWikiPages(localStorage.token, expertId);
wikiPages = res.pages;
} catch (e) {
toast.error(`${e}`);
}
};

const loadHealthReport = async () => {
try {
healthReport = await getExpertWikiHealth(localStorage.token, expertId);
} catch (e) {
toast.error(`${e}`);
}
};

const loadAll = async () => {
loading = true;
await Promise.all([loadWikiStatus(), loadWikiPages(), loadHealthReport()]);
loading = false;
};

const handleFileUpload = async (e: Event) => {
const input = e.target as HTMLInputElement;
if (!input.files?.length) return;

uploading = true;
let hasError = false;

for (const file of Array.from(input.files)) {
try {
await uploadToExpertWiki(localStorage.token, expertId, file);
} catch (e) {
toast.error(`${e}`);
hasError = true;
}
}

uploading = false;
input.value = '';

if (!hasError) {
toast.success('文件上传成功');
await loadWikiStatus();
}
};

const triggerCompile = async () => {
compiling = true;
try {
const res = await compileExpertWiki(localStorage.token, expertId);
if (res.errors?.length) {
toast.error(`编译完成，但有 ${res.errors.length} 个错误`);
} else {
toast.success('编译完成');
}
await Promise.all([loadWikiStatus(), loadWikiPages()]);
} catch (e) {
toast.error(`${e}`);
} finally {
compiling = false;
}
};

const triggerHealthCheck = async () => {
checking = true;
try {
healthReport = await triggerExpertWikiHealthCheck(localStorage.token, expertId);
toast.success('健康检查完成');
} catch (e) {
toast.error(`${e}`);
} finally {
checking = false;
}
};

const openPage = async (page: WikiPage) => {
selectedPage = page;
try {
const res = await readExpertWikiPage(localStorage.token, expertId, page.path);
pageContent = res.content;
} catch (e) {
toast.error(`${e}`);
pageContent = '';
}
};

const closePage = () => {
selectedPage = null;
pageContent = '';
};

const getSeverityIcon = (severity: string) => {
switch (severity) {
case 'high': return XMark;
case 'medium': return Bolt;
case 'low': return CheckCircle;
default: return AlertTriangle;
}
};

const getSeverityColor = (severity: string) => {
switch (severity) {
case 'high': return 'text-red-500';
case 'medium': return 'text-yellow-500';
case 'low': return 'text-blue-500';
default: return 'text-gray-500';
}
};

onMount(loadAll);
</script>

<div class="flex flex-col gap-4">
<div class="flex items-center justify-between">
<div class="text-sm font-medium text-gray-900 dark:text-gray-100">Wiki 管理</div>
<div class="text-xs text-gray-500 dark:text-gray-400">
{#if wikiStatus}
{wikiStatus.raw_files} 个原始文件 · {wikiStatus.wiki_pages} 个 Wiki 页面
{/if}
</div>
</div>

{#if loading}
<div class="flex justify-center py-8">
<Spinner className="size-5" />
</div>
{:else}
<div class="flex items-center gap-1 border-b border-gray-100 dark:border-gray-900">
<button
class="px-3 py-2 text-sm transition {activeTab === 'files'
? 'border-b-2 border-gray-900 text-gray-900 dark:border-gray-100 dark:text-gray-100'
: 'text-gray-500 hover:text-gray-700'}"
on:click={() => (activeTab = 'files')}
>
文件
</button>
<button
class="px-3 py-2 text-sm transition {activeTab === 'pages'
? 'border-b-2 border-gray-900 text-gray-900 dark:border-gray-100 dark:text-gray-100'
: 'text-gray-500 hover:text-gray-700'}"
on:click={() => (activeTab = 'pages')}
>
页面 ({wikiPages.length})
</button>
<button
class="px-3 py-2 text-sm transition {activeTab === 'health'
? 'border-b-2 border-gray-900 text-gray-900 dark:border-gray-100 dark:text-gray-100'
: 'text-gray-500 hover:text-gray-700'}"
on:click={() => (activeTab = 'health')}
>
健康检查
</button>
</div>

{#if activeTab === 'files'}
<div class="flex flex-col gap-3">
<div class="flex items-center gap-2">
<input
bind:this={fileInput}
type="file"
multiple
class="hidden"
on:change={handleFileUpload}
/>
<button
class="px-3 py-2 rounded-xl text-sm bg-gray-900 text-white dark:bg-white dark:text-gray-900 hover:opacity-90 transition flex items-center gap-2"
on:click={() => fileInput?.click()}
disabled={uploading}
>
{#if uploading}
<Spinner className="size-4" />
{:else}
<ArrowUpTray className="size-4" />
{/if}
上传文件
</button>

<button
class="px-3 py-2 rounded-xl text-sm border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-900 transition flex items-center gap-2"
on:click={triggerCompile}
disabled={compiling}
>
{#if compiling}
<Spinner className="size-4" />
{:else}
<Refresh className="size-4" />
{/if}
编译 Wiki
</button>
</div>

{#if wikiStatus}
<div class="rounded-xl border border-gray-100 dark:border-gray-900 p-4 bg-gray-50/50 dark:bg-gray-900/30">
<div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
<div class="flex items-center gap-2">
<Folder className="size-4 text-gray-400" />
<span class="text-gray-500">原始文件:</span>
<span class="font-medium text-gray-900 dark:text-gray-100">{wikiStatus.raw_files}</span>
</div>
<div class="flex items-center gap-2">
<Document className="size-4 text-gray-400" />
<span class="text-gray-500">Wiki 页面:</span>
<span class="font-medium text-gray-900 dark:text-gray-100">{wikiStatus.wiki_pages}</span>
</div>
<div class="flex items-center gap-2">
{#if wikiStatus.index_exists}
<CheckCircle className="size-4 text-green-500" />
{:else}
<XMark className="size-4 text-gray-300" />
{/if}
<span class="text-gray-500">index.md</span>
</div>
<div class="flex items-center gap-2">
{#if wikiStatus.purpose_exists}
<CheckCircle className="size-4 text-green-500" />
{:else}
<XMark className="size-4 text-gray-300" />
{/if}
<span class="text-gray-500">purpose.md</span>
</div>
</div>
</div>
{/if}
</div>

{:else if activeTab === 'pages'}
<div class="flex flex-col gap-3">
{#if wikiPages.length === 0}
<div class="rounded-xl border border-dashed border-gray-200 dark:border-gray-800 px-3 py-6 text-sm text-gray-500 text-center">
还没有 Wiki 页面，请先上传文件并编译。
</div>
{:else}
<div class="grid grid-cols-1 md:grid-cols-2 gap-2">
{#each wikiPages as page}
<button
type="button"
class="w-full text-left rounded-xl border border-gray-100 dark:border-gray-900 px-3 py-3 hover:bg-gray-50 dark:hover:bg-gray-900 transition"
on:click={() => openPage(page)}
>
<div class="text-xs text-gray-400">{page.path}</div>
<div class="mt-1 text-sm font-medium text-gray-900 dark:text-gray-100">{page.title}</div>
<div class="mt-1 text-xs text-gray-500">{page.page_type}</div>
</button>
{/each}
</div>
{/if}
</div>

{:else if activeTab === 'health'}
<div class="flex flex-col gap-3">
<button
class="px-3 py-2 rounded-xl text-sm border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-900 transition flex items-center gap-2 self-start"
on:click={triggerHealthCheck}
disabled={checking}
>
{#if checking}
<Spinner className="size-4" />
{:else}
<Refresh className="size-4" />
{/if}
重新检查
</button>

{#if healthReport}
<div class="rounded-xl border border-gray-100 dark:border-gray-900 p-4">
<div class="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">
共 {healthReport.total_pages} 个页面，发现 {healthReport.issues.length} 个问题
</div>

{#if healthReport.issues.length === 0}
<div class="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
<CheckCircle className="size-4" />
Wiki 健康状态良好
</div>
{:else}
<div class="flex flex-col gap-3">
{#each healthReport.issues as issue}
<div class="rounded-lg border border-gray-100 dark:border-gray-900 p-3">
<div class="flex items-center gap-2">
<svelte:component this={getSeverityIcon(issue.severity)} className="size-4 {getSeverityColor(issue.severity)}" />
<span class="text-sm font-medium text-gray-900 dark:text-gray-100">{issue.rule_id}</span>
<span class="text-xs text-gray-400">({issue.severity})</span>
</div>

{#if issue.pages?.length}
<div class="mt-2 text-xs text-gray-500 pl-6">
<div class="font-medium text-gray-500 mb-1">受影响页面:</div>
{#each issue.pages as page}
<div class="text-gray-600 dark:text-gray-300">{page}</div>
{/each}
</div>
{/if}

{#if issue.links?.length}
<div class="mt-2 text-xs text-gray-500 pl-6">
<div class="font-medium text-gray-500 mb-1">断链:</div>
{#each issue.links as link}
<div class="text-gray-600 dark:text-gray-300">
从 {link.from} 指向 [[{link.link}]]
</div>
{/each}
</div>
{/if}
</div>
{/each}
</div>
{/if}
</div>
{/if}
</div>
{/if}
{/if}
</div>

{#if selectedPage}
<div class="fixed inset-0 z-50 bg-black/45 backdrop-blur-[2px] p-4 md:p-6" on:click={closePage}>
<div class="w-full max-w-3xl mx-auto mt-[8vh] max-h-[80vh] overflow-auto" on:click|stopPropagation>
<div class="rounded-[20px] border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 shadow-2xl">
<div class="sticky top-0 flex items-center justify-between gap-3 px-4 py-3 border-b border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950">
<div class="min-w-0">
<div class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">{selectedPage.title}</div>
<div class="text-xs text-gray-400">{selectedPage.path}</div>
</div>
<button
type="button"
class="rounded-lg px-3 py-1.5 text-sm text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-900"
on:click={closePage}
>
关闭
</button>
</div>
<div class="p-4">
<pre class="text-sm text-gray-600 dark:text-gray-300 whitespace-pre-wrap font-mono">{pageContent}</pre>
</div>
</div>
</div>
</div>
{/if}
