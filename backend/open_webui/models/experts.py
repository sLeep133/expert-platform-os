import logging
import os
import time
from pathlib import Path
from typing import Optional

from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from open_webui.internal.db import Base, JSONField, get_async_db_context
from open_webui.models.users import User, UserModel, Users, UserResponse
from open_webui.env import DATA_DIR

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (
    BigInteger,
    Column,
    String,
    Text,
    JSON,
)

log = logging.getLogger(__name__)

####################
# Expert DB Schema
####################


class Expert(Base):
    __tablename__ = 'expert'

    id = Column(Text, unique=True, primary_key=True)
    user_id = Column(Text)

    name = Column(Text)
    description = Column(Text, nullable=True)
    avatar = Column(Text, nullable=True)
    tags = Column(JSON, default=list)
    visibility = Column(Text, default='private')

    # Wiki 根目录（每个 Expert 独立）
    wiki_root = Column(Text, nullable=True)

    # Persona
    persona_role = Column(Text, nullable=True)
    persona_tone = Column(Text, nullable=True)
    persona_style = Column(Text, nullable=True)
    persona_constraints = Column(JSON, default=list)

    # Method
    method_principles = Column(JSON, default=list)
    method_workflows = Column(JSON, default=list)
    method_output_preferences = Column(JSON, default=list)

    # Runtime
    runtime_model = Column(Text, nullable=True)
    runtime_provider = Column(Text, nullable=True)
    runtime_context_budget = Column(BigInteger, nullable=True)
    runtime_tool_policy = Column(Text, default='safe')
    runtime_collaboration_mode = Column(Text, default='solo')

    # Knowledge View
    knowledge_spaces = Column(JSON, default=list)
    knowledge_pinned_pages = Column(JSON, default=list)
    knowledge_source_filters = Column(JSON, default=list)

    # System prompt (composed from persona + method)
    system_prompt = Column(Text, nullable=True)

    meta = Column(JSON, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class ExpertModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str

    name: str
    description: Optional[str] = None
    avatar: Optional[str] = None
    tags: list[str] = []
    visibility: str = 'private'

    # Wiki 根目录（每个 Expert 独立）
    wiki_root: Optional[str] = None

    # Persona
    persona_role: Optional[str] = None
    persona_tone: Optional[str] = None
    persona_style: Optional[str] = None
    persona_constraints: list[str] = []

    # Method
    method_principles: list[str] = []
    method_workflows: list[str] = []
    method_output_preferences: list[str] = []

    # Runtime
    runtime_model: Optional[str] = None
    runtime_provider: Optional[str] = None
    runtime_context_budget: Optional[int] = None
    runtime_tool_policy: str = 'safe'
    runtime_collaboration_mode: str = 'solo'

    # Knowledge View
    knowledge_spaces: list[str] = []
    knowledge_pinned_pages: list[str] = []
    knowledge_source_filters: list[str] = []

    system_prompt: Optional[str] = None

    meta: Optional[dict] = None

    created_at: int
    updated_at: int


####################
# Forms
####################


class PersonaForm(BaseModel):
    role: Optional[str] = None
    tone: Optional[str] = None
    style: Optional[str] = None
    constraints: list[str] = []


class MethodForm(BaseModel):
    principles: list[str] = []
    workflows: list[str] = []
    output_preferences: list[str] = []


class RuntimeForm(BaseModel):
    model: Optional[str] = None
    provider: Optional[str] = None
    context_budget: Optional[int] = None
    tool_policy: str = 'safe'
    collaboration_mode: str = 'solo'


class KnowledgeViewForm(BaseModel):
    spaces: list[str] = []
    pinned_pages: list[str] = []
    source_filters: list[str] = []


class ExpertForm(BaseModel):
    name: str
    description: Optional[str] = None
    avatar: Optional[str] = None
    tags: list[str] = []
    visibility: str = 'private'

    persona: Optional[PersonaForm] = None
    method: Optional[MethodForm] = None
    runtime: Optional[RuntimeForm] = None
    knowledge_view: Optional[KnowledgeViewForm] = None

    system_prompt: Optional[str] = None


class ExpertUserModel(ExpertModel):
    user: Optional[UserResponse] = None


class ExpertResponse(ExpertModel):
    pass


class ExpertListResponse(BaseModel):
    items: list[ExpertUserModel]
    total: int


####################
# Table Operations
####################


import uuid


class ExpertTable:
    def _create_expert_wiki(self, expert_id: str) -> str:
        """创建 Expert 的 Wiki 目录结构"""
        wiki_root = DATA_DIR / 'experts' / expert_id
        (wiki_root / 'raw' / 'articles').mkdir(parents=True, exist_ok=True)
        (wiki_root / 'raw' / 'pdfs').mkdir(parents=True, exist_ok=True)
        (wiki_root / 'raw' / 'notes').mkdir(parents=True, exist_ok=True)
        (wiki_root / 'raw' / 'assets').mkdir(parents=True, exist_ok=True)
        (wiki_root / 'wiki' / 'entities').mkdir(parents=True, exist_ok=True)
        (wiki_root / 'wiki' / 'topics').mkdir(parents=True, exist_ok=True)
        (wiki_root / 'wiki' / 'sources').mkdir(parents=True, exist_ok=True)
        (wiki_root / 'wiki' / 'synthesis').mkdir(parents=True, exist_ok=True)
        (wiki_root / 'wiki' / 'synthesis' / 'sessions').mkdir(parents=True, exist_ok=True)
        # 创建 index.md
        index_path = wiki_root / 'index.md'
        if not index_path.exists():
            index_path.write_text('# Wiki Index\n\n', encoding='utf-8')
        # 创建 log.md
        log_path = wiki_root / 'log.md'
        if not log_path.exists():
            log_path.write_text('# Operation Log\n\n', encoding='utf-8')
        # 创建 purpose.md
        purpose_path = wiki_root / 'purpose.md'
        if not purpose_path.exists():
            purpose_path.write_text('# Research Direction\n\n', encoding='utf-8')
        return str(wiki_root)

    async def insert_new_expert(
        self, user_id: str, form_data: ExpertForm
    ) -> Optional[ExpertModel]:
        async with get_async_db_context() as db:
            expert_id = str(uuid.uuid4())
            now = int(time.time())

            persona = form_data.persona or PersonaForm()
            method = form_data.method or MethodForm()
            runtime = form_data.runtime or RuntimeForm()
            knowledge_view = form_data.knowledge_view or KnowledgeViewForm()

            # 创建 Expert Wiki 目录
            wiki_root = self._create_expert_wiki(expert_id)

            expert = Expert(
                id=expert_id,
                user_id=user_id,
                name=form_data.name,
                description=form_data.description,
                avatar=form_data.avatar,
                tags=form_data.tags,
                visibility=form_data.visibility,
                persona_role=persona.role,
                persona_tone=persona.tone,
                persona_style=persona.style,
                persona_constraints=persona.constraints,
                method_principles=method.principles,
                method_workflows=method.workflows,
                method_output_preferences=method.output_preferences,
                runtime_model=runtime.model,
                runtime_provider=runtime.provider,
                runtime_context_budget=runtime.context_budget,
                runtime_tool_policy=runtime.tool_policy,
                runtime_collaboration_mode=runtime.collaboration_mode,
                knowledge_spaces=knowledge_view.spaces,
                knowledge_pinned_pages=knowledge_view.pinned_pages,
                knowledge_source_filters=knowledge_view.source_filters,
                system_prompt=form_data.system_prompt,
                wiki_root=wiki_root,
                created_at=now,
                updated_at=now,
            )

            try:
                db.add(expert)
                await db.commit()
                await db.refresh(expert)
                return ExpertModel.model_validate(expert)
            except Exception as e:
                log.exception(e)
                return None

    async def get_expert_by_id(self, id: str) -> Optional[ExpertModel]:
        async with get_async_db_context() as db:
            result = await db.execute(select(Expert).filter_by(id=id))
            expert = result.scalars().first()
            return ExpertModel.model_validate(expert) if expert else None

    async def get_experts(self) -> list[ExpertUserModel]:
        async with get_async_db_context() as db:
            result = await db.execute(select(Expert).order_by(Expert.updated_at.desc()))
            experts = result.scalars().all()

            user_ids = list(set(e.user_id for e in experts))
            users = await Users.get_users_by_user_ids(user_ids, db=db) if user_ids else []
            users_dict = {u.id: u for u in users}

            items = []
            for expert in experts:
                user = users_dict.get(expert.user_id)
                items.append(
                    ExpertUserModel(
                        **ExpertModel.model_validate(expert).model_dump(),
                        user=UserResponse(**UserModel.model_validate(user).model_dump()) if user else None,
                    )
                )
            return items

    async def get_experts_by_user_id(self, user_id: str) -> list[ExpertUserModel]:
        async with get_async_db_context() as db:
            result = await db.execute(
                select(Expert)
                .filter((Expert.user_id == user_id) | (Expert.visibility == 'shared'))
                .order_by(Expert.updated_at.desc())
            )
            experts = result.scalars().all()

            user_ids = list(set(e.user_id for e in experts))
            users = await Users.get_users_by_user_ids(user_ids, db=db) if user_ids else []
            users_dict = {u.id: u for u in users}

            items = []
            for expert in experts:
                user = users_dict.get(expert.user_id)
                items.append(
                    ExpertUserModel(
                        **ExpertModel.model_validate(expert).model_dump(),
                        user=UserResponse(**UserModel.model_validate(user).model_dump()) if user else None,
                    )
                )
            return items

    async def update_expert_by_id(
        self, id: str, form_data: ExpertForm
    ) -> Optional[ExpertModel]:
        async with get_async_db_context() as db:
            persona = form_data.persona or PersonaForm()
            method = form_data.method or MethodForm()
            runtime = form_data.runtime or RuntimeForm()
            knowledge_view = form_data.knowledge_view or KnowledgeViewForm()

            values = {
                'name': form_data.name,
                'description': form_data.description,
                'avatar': form_data.avatar,
                'tags': form_data.tags,
                'visibility': form_data.visibility,
                'persona_role': persona.role,
                'persona_tone': persona.tone,
                'persona_style': persona.style,
                'persona_constraints': persona.constraints,
                'method_principles': method.principles,
                'method_workflows': method.workflows,
                'method_output_preferences': method.output_preferences,
                'runtime_model': runtime.model,
                'runtime_provider': runtime.provider,
                'runtime_context_budget': runtime.context_budget,
                'runtime_tool_policy': runtime.tool_policy,
                'runtime_collaboration_mode': runtime.collaboration_mode,
                'knowledge_spaces': knowledge_view.spaces,
                'knowledge_pinned_pages': knowledge_view.pinned_pages,
                'knowledge_source_filters': knowledge_view.source_filters,
                'system_prompt': form_data.system_prompt,
                'updated_at': int(time.time()),
            }

            await db.execute(update(Expert).filter_by(id=id).values(**values))
            await db.commit()
            return await self.get_expert_by_id(id)

    async def delete_expert_by_id(self, id: str) -> bool:
        async with get_async_db_context() as db:
            try:
                await db.execute(delete(Expert).filter_by(id=id))
                await db.commit()
                return True
            except Exception:
                return False


Experts = ExpertTable()
