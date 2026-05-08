import logging
from typing import Optional
import os
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import FileResponse

from open_webui.models.experts import (
    ExpertForm,
    ExpertModel,
    ExpertResponse,
    ExpertUserModel,
    Experts,
)
from open_webui.models.users import UserModel
from open_webui.utils.auth import get_verified_user

from open_webui.knowledge.wiki import (
    WikiRetriever,
    WikiHealthChecker,
    ensure_wiki_structure,
    get_expert_wiki_root,
)
from open_webui.knowledge.compiler import compile_expert_wiki

log = logging.getLogger(__name__)

router = APIRouter()


############################
# GetExperts
############################


@router.get('/', response_model=list[ExpertUserModel])
async def get_experts(user=Depends(get_verified_user)):
    if user.role == 'admin':
        return await Experts.get_experts()
    return await Experts.get_experts_by_user_id(user.id)


############################
# CreateNewExpert
############################


@router.post('/create', response_model=Optional[ExpertResponse])
async def create_new_expert(
    form_data: ExpertForm,
    user=Depends(get_verified_user),
):
    expert = await Experts.insert_new_expert(user.id, form_data)
    if expert:
        return expert
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail='Failed to create expert.',
    )


############################
# GetExpertById
############################


@router.get('/{id}', response_model=Optional[ExpertResponse])
async def get_expert_by_id(id: str, user=Depends(get_verified_user)):
    expert = await Experts.get_expert_by_id(id)
    if not expert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Expert not found.',
        )
    if expert.user_id != user.id and expert.visibility != 'shared' and user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Access prohibited.',
        )
    return expert


############################
# UpdateExpertById
############################


@router.post('/{id}/update', response_model=Optional[ExpertResponse])
async def update_expert_by_id(
    id: str,
    form_data: ExpertForm,
    user=Depends(get_verified_user),
):
    expert = await Experts.get_expert_by_id(id)
    if not expert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Expert not found.',
        )
    if expert.user_id != user.id and user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Access prohibited.',
        )
    updated = await Experts.update_expert_by_id(id, form_data)
    if updated:
        return updated
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail='Failed to update expert.',
    )


############################
# DeleteExpertById
############################


@router.delete('/{id}/delete', response_model=bool)
async def delete_expert_by_id(id: str, user=Depends(get_verified_user)):
    expert = await Experts.get_expert_by_id(id)
    if not expert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Expert not found.',
        )
    if expert.user_id != user.id and user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Access prohibited.',
        )
    return await Experts.delete_expert_by_id(id)


############################
# DuplicateExpert
############################


@router.post('/{id}/duplicate', response_model=Optional[ExpertResponse])
async def duplicate_expert_by_id(id: str, user=Depends(get_verified_user)):
    expert = await Experts.get_expert_by_id(id)
    if not expert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Expert not found.',
        )

    from open_webui.models.experts import (
        PersonaForm,
        MethodForm,
        RuntimeForm,
        KnowledgeViewForm,
    )

    form_data = ExpertForm(
        name=f'{expert.name} (Copy)',
        description=expert.description,
        avatar=expert.avatar,
        tags=expert.tags,
        visibility='private',
        persona=PersonaForm(
            role=expert.persona_role,
            tone=expert.persona_tone,
            style=expert.persona_style,
            constraints=expert.persona_constraints,
        ),
        method=MethodForm(
            principles=expert.method_principles,
            workflows=expert.method_workflows,
            output_preferences=expert.method_output_preferences,
        ),
        runtime=RuntimeForm(
            model=expert.runtime_model,
            provider=expert.runtime_provider,
            context_budget=expert.runtime_context_budget,
            tool_policy=expert.runtime_tool_policy,
            collaboration_mode=expert.runtime_collaboration_mode,
        ),
        knowledge_view=KnowledgeViewForm(
            spaces=expert.knowledge_spaces,
            pinned_pages=expert.knowledge_pinned_pages,
            source_filters=expert.knowledge_source_filters,
        ),
        system_prompt=expert.system_prompt,
    )

    new_expert = await Experts.insert_new_expert(user.id, form_data)
    if new_expert:
        return new_expert
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail='Failed to duplicate expert.',
    )


############################
# Wiki API - Expert 私有 Wiki
############################


@router.get('/{id}/wiki/status')
async def get_expert_wiki_status(id: str, user=Depends(get_verified_user)):
    """获取 Expert Wiki 状态"""
    expert = await Experts.get_expert_by_id(id)
    if not expert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Expert not found.',
        )
    if expert.user_id != user.id and user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Access prohibited.',
        )

    wiki_root = Path(expert.wiki_root) if expert.wiki_root else get_expert_wiki_root(id)

    if not wiki_root.exists():
        ensure_wiki_structure(id)
        wiki_root = get_expert_wiki_root(id)

    # 统计信息
    raw_count = len(list((wiki_root / 'raw').rglob('*'))) if (wiki_root / 'raw').exists() else 0
    wiki_pages = list((wiki_root / 'wiki').rglob('*.md')) if (wiki_root / 'wiki').exists() else []

    return {
        'expert_id': id,
        'wiki_root': str(wiki_root),
        'raw_files': raw_count,
        'wiki_pages': len(wiki_pages),
        'index_exists': (wiki_root / 'index.md').exists(),
        'log_exists': (wiki_root / 'log.md').exists(),
        'purpose_exists': (wiki_root / 'purpose.md').exists(),
    }


@router.get('/{id}/wiki/pages')
async def list_expert_wiki_pages(id: str, user=Depends(get_verified_user)):
    """列出 Expert Wiki 的所有页面"""
    expert = await Experts.get_expert_by_id(id)
    if not expert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Expert not found.',
        )
    if expert.user_id != user.id and user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Access prohibited.',
        )

    wiki_root = Path(expert.wiki_root) if expert.wiki_root else get_expert_wiki_root(id)
    retriever = WikiRetriever(str(wiki_root))
    pages = retriever.list_wiki_pages()

    return {
        'expert_id': id,
        'pages': [p.to_dict() for p in pages],
    }


@router.get('/{id}/wiki/page/{path:path}')
async def read_expert_wiki_page(id: str, path: str, user=Depends(get_verified_user)):
    """读取指定 Wiki 页内容"""
    expert = await Experts.get_expert_by_id(id)
    if not expert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Expert not found.',
        )
    if expert.user_id != user.id and user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Access prohibited.',
        )

    wiki_root = Path(expert.wiki_root) if expert.wiki_root else get_expert_wiki_root(id)
    retriever = WikiRetriever(str(wiki_root))
    content = retriever.read_wiki_page(path)

    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Wiki page not found.',
        )

    return {
        'expert_id': id,
        'path': path,
        'content': content,
    }


@router.post('/{id}/wiki/upload')
async def upload_to_expert_wiki(
    id: str,
    file: UploadFile = File(...),
    user=Depends(get_verified_user),
):
    """上传文件到 Expert 的 Wiki raw 目录（强制绑定 Expert）"""
    expert = await Experts.get_expert_by_id(id)
    if not expert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Expert not found.',
        )
    if expert.user_id != user.id and user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Access prohibited.',
        )

    # 确保 Wiki 目录存在
    wiki_root = Path(expert.wiki_root) if expert.wiki_root else get_expert_wiki_root(id)
    if not wiki_root.exists():
        ensure_wiki_structure(id)
        wiki_root = Path(expert.wiki_root) if expert.wiki_root else get_expert_wiki_root(id)

    # 保存到 raw 目录
    raw_dir = wiki_root / 'raw'
    file_path = raw_dir / file.filename

    try:
        contents = await file.read()
        file_path.write_bytes(contents)

        return {
            'expert_id': id,
            'file': file.filename,
            'path': str(file_path.relative_to(wiki_root)),
            'size': len(contents),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to save file: {str(e)}',
        )


@router.post('/{id}/wiki/compile')
async def compile_expert_wiki_api(
    id: str,
    file_path: Optional[str] = Form(None),
    user=Depends(get_verified_user),
):
    """触发 Expert Wiki 编译"""
    expert = await Experts.get_expert_by_id(id)
    if not expert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Expert not found.',
        )
    if expert.user_id != user.id and user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Access prohibited.',
        )

    # 使用 Expert 自己配置的模型（如果有）
    llm_config = None
    if expert.runtime_model:
        llm_config = {'model': expert.runtime_model}

    result = await compile_expert_wiki(id, file_path, llm_config=llm_config)

    return {
        'expert_id': id,
        'status': result.status,
        'pages': result.pages,
        'errors': result.errors,
        'duration': result.duration,
    }


@router.get('/{id}/wiki/compile/status')
async def get_expert_wiki_compile_status(id: str, user=Depends(get_verified_user)):
    """获取 Expert Wiki 编译状态"""
    expert = await Experts.get_expert_by_id(id)
    if not expert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Expert not found.',
        )
    if expert.user_id != user.id and user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Access prohibited.',
        )

    wiki_root = Path(expert.wiki_root) if expert.wiki_root else get_expert_wiki_root(id)
    cache_file = wiki_root / '.wiki-cache.json'

    if cache_file.exists():
        import json
        try:
            cache = json.loads(cache_file.read_text(encoding='utf-8'))
            return {
                'expert_id': id,
                'cache': cache,
            }
        except Exception:
            pass

    return {
        'expert_id': id,
        'cache': None,
    }


@router.get('/{id}/wiki/health')
async def get_expert_wiki_health(id: str, user=Depends(get_verified_user)):
    """获取 Expert Wiki 健康检查报告"""
    expert = await Experts.get_expert_by_id(id)
    if not expert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Expert not found.',
        )
    if expert.user_id != user.id and user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Access prohibited.',
        )

    wiki_root = Path(expert.wiki_root) if expert.wiki_root else get_expert_wiki_root(id)
    checker = WikiHealthChecker(str(wiki_root))

    report = await checker.check_all()

    return report


@router.post('/{id}/wiki/health-check')
async def trigger_expert_wiki_health_check(id: str, user=Depends(get_verified_user)):
    """手动触发 Expert Wiki 健康检查"""
    expert = await Experts.get_expert_by_id(id)
    if not expert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Expert not found.',
        )
    if expert.user_id != user.id and user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Access prohibited.',
        )

    wiki_root = Path(expert.wiki_root) if expert.wiki_root else get_expert_wiki_root(id)
    checker = WikiHealthChecker(str(wiki_root))

    report = await checker.check_all()

    return report

