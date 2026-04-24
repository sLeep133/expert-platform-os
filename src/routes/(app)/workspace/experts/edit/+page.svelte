<script lang="ts">
import { goto } from '$app/navigation';
import { page } from '$app/stores';
import { getContext, onMount } from 'svelte';
import { toast } from 'svelte-sonner';

import { getExpertById, updateExpertById } from '$lib/apis/experts';
import ExpertEditor from '$lib/components/workspace/Experts/ExpertEditor.svelte';
import Spinner from '$lib/components/common/Spinner.svelte';

const i18n = getContext('i18n');

let expert = null;

const onSubmit = async (form) => {
const res = await updateExpertById(localStorage.token, expert.id, form).catch((error) => {
toast.error(`${error}`);
return null;
});

if (res) {
toast.success($i18n.t('Expert updated successfully'));
expert = res;
}
};

onMount(async () => {
const id = $page.url.searchParams.get('id');
if (!id) {
goto('/workspace/experts');
return;
}

expert = await getExpertById(localStorage.token, id).catch((error) => {
toast.error(`${error}`);
goto('/workspace/experts');
return null;
});
});
</script>

{#if expert}
<ExpertEditor {expert} onSubmit={onSubmit} />
{:else}
<div class="flex justify-center py-12">
<Spinner className="size-5" />
</div>
{/if}
