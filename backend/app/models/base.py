from typing import Optional, List
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship
from uuid import UUID, uuid4


class User(SQLModel, table=True):
    """User model to store authentication and profile information"""
    id: Optional[int] = Field(default=None, primary_key=True)
    uuid: UUID = Field(default_factory=uuid4, index=True, unique=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    sessions: List["Session"] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete"})
    chat_sessions: List["ChatSession"] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete"})
    agents: List["Agent"] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete"})
    mcp_servers: List["MCPServer"] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete"})


class Session(SQLModel, table=True):
    """Session model to store user sessions"""
    id: Optional[int] = Field(default=None, primary_key=True)
    uuid: UUID = Field(default_factory=uuid4, index=True, unique=True)
    user_id: int = Field(foreign_key="user.id")
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: User = Relationship(back_populates="sessions")


class Agent(SQLModel, table=True):
    """Agent model to store agent information"""
    id: Optional[int] = Field(default=None, primary_key=True)
    uuid: UUID = Field(default_factory=uuid4, index=True, unique=True)
    user_id: int = Field(foreign_key="user.id")
    name: str
    description: Optional[str] = None
    system_prompt: str  # The agent blueprint/system prompt
    is_default: bool = Field(default=False)  # If this is the default Tooler agent
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: User = Relationship(back_populates="agents")
    chat_sessions: List["ChatSession"] = Relationship(back_populates="agent", sa_relationship_kwargs={"cascade": "all, delete"})
    agent_mcp_servers: List["AgentMCPServer"] = Relationship(back_populates="agent", sa_relationship_kwargs={"cascade": "all, delete"})


class MCPServer(SQLModel, table=True):
    """MCP Server model to store MCP server information"""
    id: Optional[int] = Field(default=None, primary_key=True)
    uuid: UUID = Field(default_factory=uuid4, index=True, unique=True)
    user_id: int = Field(foreign_key="user.id")
    name: str
    description: Optional[str] = None
    code: str  # The MCP server code
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: User = Relationship(back_populates="mcp_servers")
    agent_mcp_servers: List["AgentMCPServer"] = Relationship(back_populates="mcp_server", sa_relationship_kwargs={"cascade": "all, delete"})


class AgentMCPServer(SQLModel, table=True):
    """Relationship table between Agent and MCP Server"""
    agent_id: int = Field(foreign_key="agent.id", primary_key=True)
    mcp_server_id: int = Field(foreign_key="mcp_server.id", primary_key=True)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    agent: Agent = Relationship(back_populates="agent_mcp_servers")
    mcp_server: MCPServer = Relationship(back_populates="agent_mcp_servers")


class ChatSession(SQLModel, table=True):
    """Chat Session model to store chat conversations"""
    id: Optional[int] = Field(default=None, primary_key=True)
    uuid: UUID = Field(default_factory=uuid4, index=True, unique=True)
    user_id: int = Field(foreign_key="user.id")
    agent_id: int = Field(foreign_key="agent.id")
    title: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: User = Relationship(back_populates="chat_sessions")
    agent: Agent = Relationship(back_populates="chat_sessions")
    messages: List["Message"] = Relationship(back_populates="chat_session", sa_relationship_kwargs={"cascade": "all, delete"})


class Message(SQLModel, table=True):
    """Message model to store chat messages"""
    id: Optional[int] = Field(default=None, primary_key=True)
    uuid: UUID = Field(default_factory=uuid4, index=True, unique=True)
    chat_session_id: int = Field(foreign_key="chatsession.id")
    role: str  # 'user' or 'model'
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    chat_session: ChatSession = Relationship(back_populates="messages")
