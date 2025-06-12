import os
import json
import subprocess
import logging
import gzip
from pathlib import Path
from typing import List, Optional, Dict, AsyncIterator, Literal
from contextlib import asynccontextmanager

from pydantic import BaseModel, Field, conlist
from mcp.server.fastmcp import FastMCP, Context

# ---------------------------
# Logging Setup
# ---------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

log_dir = Path("logs")
log_dir.mkdir(parents=True, exist_ok=True)
log_path = log_dir / "server.log"

handler = logging.handlers.TimedRotatingFileHandler(
    filename=str(log_path),
    when="midnight",
    interval=1,
    backupCount=7,
    encoding="utf-8",
    utc=True,
)
# Compress old log files
handler.rotator = lambda source, dest: (
    gzip.open(dest + ".gz", 'wb').write(Path(source).read_bytes()),
    os.remove(source)
)
handler.namer = lambda name: name + ".gz"
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# ---------------------------
# Environment and Paths
# ---------------------------
ROOT_FOLDER = Path(os.getenv("ROOT_FOLDER", "./projects")).expanduser()
ROOT_FOLDER.mkdir(parents=True, exist_ok=True)

# ---------------------------
# Lifespan Context
# ---------------------------
class LifespanContext(BaseModel):
    current_project: Optional[str] = Field(
        None, description="Name of the current project"
    )

@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[LifespanContext]:
    """Manage application startup and shutdown, storing current project state."""
    context = LifespanContext()
    yield context

# ---------------------------
# FastMCP Server Initialization
# ---------------------------
mcp = FastMCP("ProjectTools", lifespan=app_lifespan)

# ---------------------------
# BaseModel Definitions
# ---------------------------
class CreateProjectRequest(BaseModel):
    project_name: str = Field(..., description="Name of the new project to create")

class CreateProjectResponse(BaseModel):
    project_name: str = Field(..., description="Name of the created project")
    path: str = Field(..., description="Relative path of the project directory")

class ListProjectsResponse(BaseModel):
    projects: List[str] = Field(..., description="List of existing project names")

class CreateFoldersRequest(BaseModel):
    paths: List[str] = Field(
        ..., description="List of folder paths to create, relative to current project"
    )

class CreateFoldersResponse(BaseModel):
    created: List[str] = Field(..., description="List of created folder paths")

class ListFolderContentsRequest(BaseModel):
    path: Optional[str] = Field(
        None, description="Folder path to list, relative to current project"
    )

class ListFolderContentsResponse(BaseModel):
    folders: List[str] = Field(..., description="List of subfolders")
    files: List[str] = Field(..., description="List of files")

class RenameEntryRequest(BaseModel):
    old_path: str = Field(..., description="Existing file or folder path, relative to project")
    new_name: str = Field(..., description="New name for file or folder")

class RenameEntryResponse(BaseModel):
    new_path: str = Field(..., description="New path of the renamed entry")

class ReadFileRequest(BaseModel):
    path: str = Field(..., description="File path to read, relative to project")

class ReadFileResponse(BaseModel):
    content: str = Field(..., description="Text content of the file")

class WriteFileRequest(BaseModel):
    path: str = Field(..., description="File path to rewrite, relative to project")
    content: str = Field(..., description="New content for the file")

class RewriteFileResponse(BaseModel):
    success: bool = Field(..., description="Whether the rewrite was successful")

class SetVariablesRequest(BaseModel):
    variables: Dict[str, str] = Field(..., description="Variables to set or update")

class SetVariablesResponse(BaseModel):
    keys: List[str] = Field(..., description="List of variable keys set")

class GetVariableRequest(BaseModel):
    key: str = Field(..., description="Key of the variable to retrieve")

class GetVariableResponse(BaseModel):
    value: Optional[str] = Field(None, description="Value of the variable, if exists")

class DeleteVariablesRequest(BaseModel):
    keys: List[str] = Field(..., description="List of variable keys to delete")

class DeleteVariablesResponse(BaseModel):
    deleted: List[str] = Field(..., description="List of variable keys deleted")

class ListVariablesResponse(BaseModel):
    keys: List[str] = Field(..., description="All available variable keys")

class DiffVariablesRequest(BaseModel):
    key1: str = Field(..., description="First variable key for diff")
    key2: str = Field(..., description="Second variable key for diff")

class DiffVariablesResponse(BaseModel):
    diff: str = Field(..., description="Unified diff between variable values")

class GitToolRequest(BaseModel):
    command: Literal['init', 'add', 'commit', 'checkout', 'branch', 'merge', 'diff', 'revert', 'remote', 'pull', 'push'] = Field(
        ..., description="Git command to execute"
    )
    args: Optional[List[str]] = Field(None, description="Additional arguments for the git command")
    message: Optional[str] = Field(None, description="Commit message for 'commit' command")
    remote_name: Optional[str] = Field(None, description="Remote name for remote operations (e.g., 'origin')")
    remote_url: Optional[str] = Field(None, description="Remote URL for 'remote add' operation")
    branch: Optional[str] = Field(None, description="Branch name for pull/push operations")

class GitToolResponse(BaseModel):
    output: str = Field(..., description="stdout and stderr of the git command")

# New models for Git Clone functionality
class GitCloneRequest(BaseModel):
    repository_url: str = Field(..., description="URL of the git repository to clone")
    project_name: Optional[str] = Field(None, description="Name for the project folder (defaults to repository name)")
    branch: Optional[str] = Field(None, description="Specific branch to clone")
    depth: Optional[int] = Field(None, description="Create a shallow clone with a history truncated to the specified number of commits")

class GitCloneResponse(BaseModel):
    project_name: str = Field(..., description="Name of the created project")
    path: str = Field(..., description="Relative path of the project directory")
    output: str = Field(..., description="stdout and stderr of the git clone command")

class MCPPromptRequest(BaseModel):
    client_path: str = Field(..., description="The path to the client file who's functionality the MCP server wraps.")

class AgentPromptRequest(BaseModel):
    agent_name: str = Field(..., description="The name of the agent. Choose a simple single word name which describes the agent")

class A2APromptRequest(BaseModel):
    agent_name: str = Field(..., description="The name of the agent. Choose a simple single word name which describes the agent")
    

# ---------------------------
# Helper Functions
# ---------------------------
def _get_project_dir(ctx: Context) -> Path:
    project = ctx.request_context.lifespan_context.current_project
    if not project:
        raise ValueError("No current project set. Use set_current_project first.")
    proj_dir = ROOT_FOLDER / project
    if not proj_dir.exists():
        raise FileNotFoundError(f"Project directory not found: {proj_dir}")
    return proj_dir

# ---------------------------
# Tool Implementations
# ---------------------------
@mcp.tool()
async def create_project(request: CreateProjectRequest, ctx: Context) -> CreateProjectResponse:
    """Create a new project directory and initialize variable storage."""
    project_dir = ROOT_FOLDER / request.project_name
    if project_dir.exists():
        raise FileExistsError(f"Project '{request.project_name}' already exists.")
    project_dir.mkdir(parents=True, exist_ok=False)
    # Initialize empty variables file
    (project_dir / ".variables.json").write_text(json.dumps({}))
    # Set as current project
    ctx.request_context.lifespan_context.current_project = request.project_name
    logger.info(f"Created project: {request.project_name}")
    return CreateProjectResponse(
        project_name=request.project_name,
        path=str(project_dir.relative_to(ROOT_FOLDER))
    )

@mcp.tool()
async def get_current_project(ctx: Context) -> Dict:
    """Returns the current project name."""
    project = ctx.request_context.lifespan_context.current_project
    return {'current_project': project}

@mcp.tool()
async def set_current_project(request: CreateProjectRequest, ctx: Context) -> CreateProjectResponse:
    """Set the active project by name."""
    project_dir = ROOT_FOLDER / request.project_name
    if not project_dir.exists():
        raise FileNotFoundError(f"Project '{request.project_name}' does not exist.")
    ctx.request_context.lifespan_context.current_project = request.project_name
    logger.info(f"Set current project to: {request.project_name}")
    return CreateProjectResponse(
        project_name=request.project_name,
        path=str(project_dir.relative_to(ROOT_FOLDER))
    )

@mcp.tool()
async def list_projects(ctx: Context) -> ListProjectsResponse:
    """List all existing projects."""
    projects = [p.name for p in ROOT_FOLDER.iterdir() if p.is_dir()]
    return ListProjectsResponse(projects=projects)

@mcp.tool()
async def create_folders(request: CreateFoldersRequest, ctx: Context) -> CreateFoldersResponse:
    """Create folders in the current project."""
    proj_dir = _get_project_dir(ctx)
    created = []
    for rel in request.paths:
        path = proj_dir / rel
        path.mkdir(parents=True, exist_ok=True)
        created.append(str(path.relative_to(proj_dir)))
    return CreateFoldersResponse(created=created)

@mcp.tool()
async def list_folder_contents(request: ListFolderContentsRequest, ctx: Context) -> ListFolderContentsResponse:
    """List files and folders of a directory in the current project."""
    proj_dir = _get_project_dir(ctx)
    target = proj_dir / request.path if request.path else proj_dir
    if not target.exists() or not target.is_dir():
        raise FileNotFoundError(f"Directory not found: {target}")
    folders = [d.name for d in target.iterdir() if d.is_dir()]
    files = [f.name for f in target.iterdir() if f.is_file()]
    return ListFolderContentsResponse(folders=folders, files=files)

@mcp.tool()
async def rename_entry(request: RenameEntryRequest, ctx: Context) -> RenameEntryResponse:
    """Rename file or folder within the current project."""
    proj_dir = _get_project_dir(ctx)
    old_path = proj_dir / request.old_path
    if not old_path.exists():
        raise FileNotFoundError(f"Entry not found: {old_path}")
    new_path = old_path.parent / request.new_name
    old_path.rename(new_path)
    return RenameEntryResponse(new_path=str(new_path.relative_to(proj_dir)))

@mcp.tool()
async def read_file(request: ReadFileRequest, ctx: Context) -> ReadFileResponse:
    """Read text content of a file in the current project."""
    proj_dir = _get_project_dir(ctx)
    file_path = proj_dir / request.path
    if not file_path.exists() or not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")
    content = file_path.read_text(encoding="utf-8")
    return ReadFileResponse(content=content)

@mcp.tool()
async def write_file(request: WriteFileRequest, ctx: Context) -> RewriteFileResponse:
    """Overwrite a file's content in the current project. Will create file if it path doesn't exist"""
    proj_dir = _get_project_dir(ctx)
    file_path = proj_dir / request.path
    if not file_path.exists() or not file_path.is_file():
        file_path.touch(exist_ok=True)
    file_path.write_text(request.content, encoding="utf-8")
    return RewriteFileResponse(success=True)

# Variable storage helper

def _load_vars(proj_dir: Path) -> Dict[str, str]:
    var_file = proj_dir / ".variables.json"
    if not var_file.exists():
        return {}
    return json.loads(var_file.read_text(encoding="utf-8"))

def _save_vars(proj_dir: Path, vars: Dict[str, str]) -> None:
    (proj_dir / ".variables.json").write_text(json.dumps(vars, indent=2))

@mcp.tool()
async def set_variables(request: SetVariablesRequest, ctx: Context) -> SetVariablesResponse:
    """Set or update variables for the current project. Use this to remember data important to your current task."""
    proj_dir = _get_project_dir(ctx)
    vars_store = _load_vars(proj_dir)
    vars_store.update(request.variables)
    _save_vars(proj_dir, vars_store)
    return SetVariablesResponse(keys=list(request.variables.keys()))

@mcp.tool()
async def get_variable(request: GetVariableRequest, ctx: Context) -> GetVariableResponse:
    """Retrieve a variable value by key for the current project. Recall something you remembered."""
    proj_dir = _get_project_dir(ctx)
    vars_store = _load_vars(proj_dir)
    return GetVariableResponse(value=vars_store.get(request.key))

@mcp.tool()
async def delete_variables(request: DeleteVariablesRequest, ctx: Context) -> DeleteVariablesResponse:
    """Delete variables by keys for the current project. Use this to forget."""
    proj_dir = _get_project_dir(ctx)
    vars_store = _load_vars(proj_dir)
    deleted = []
    for key in request.keys:
        if key in vars_store:
            vars_store.pop(key)
            deleted.append(key)
    _save_vars(proj_dir, vars_store)
    return DeleteVariablesResponse(deleted=deleted)

@mcp.tool()
async def list_variables(ctx: Context) -> ListVariablesResponse:
    """List all variable keys for the current project. Shows what you are currently remembering."""
    proj_dir = _get_project_dir(ctx)
    vars_store = _load_vars(proj_dir)
    return ListVariablesResponse(keys=list(vars_store.keys()))

@mcp.tool()
async def diff_variables(request: DiffVariablesRequest, ctx: Context) -> DiffVariablesResponse:
    """Generate a unified diff between two variable values."""
    proj_dir = _get_project_dir(ctx)
    vars_store = _load_vars(proj_dir)
    v1 = vars_store.get(request.key1, "")
    v2 = vars_store.get(request.key2, "")
    import difflib
    diff = ''.join(difflib.unified_diff(
        v1.splitlines(keepends=True),
        v2.splitlines(keepends=True),
        fromfile=request.key1,
        tofile=request.key2
    ))
    return DiffVariablesResponse(diff=diff)

@mcp.tool()
async def get_absolute_project_root_folder(ctx: Context) -> Dict:
    """Gets the absolute root folder path for the current project. Use this with external tools when a full path is necessary as a parameter."""
    proj_dir = _get_project_dir(ctx)
    return {'mcp_server_instructions': str(proj_dir.resolve())}


@mcp.tool()
async def get_mcp_server_instructions(request: MCPPromptRequest, ctx: Context) -> Dict:
    """Gets the instructions on how to code the MCP Server. Does not save to a file."""
    proj_dir = _get_project_dir(ctx)
    cfp = proj_dir / request.client_path
    client_code = cfp.read_text(encoding="utf-8")
    with open('./src/agents/mcp.md', 'r') as f:
        prompt = f.read().replace('{code}', client_code)
    return {'mcp_server_instructions': prompt}

@mcp.tool()
async def get_agent_instructions(request: AgentPromptRequest, ctx: Context) -> Dict:
    """Gets the instructions on how to code an Agent for end-to-end testing. Does not save to a file."""
    proj_dir = _get_project_dir(ctx)
    with open('./src/agents/pydantic_agent.md', 'r') as f:
        prompt = f.read().replace('{project_path}', str(proj_dir.relative_to('./'))).replace('{agent_name}', request.agent_name)
    return {'agent_creation_instructions': prompt}

@mcp.tool()
async def get_a2a_instructions(request: A2APromptRequest, ctx: Context) -> Dict:
    """Gets the instructions on how to set up an A2A Card Agent2Agent protocol."""
    proj_dir = _get_project_dir(ctx)
    with open('./src/agents/a2a.md', 'r') as f:
        prompt = f.read().replace('{project_path}', str(proj_dir.relative_to('./'))).replace('{agent_name}', request.agent_name)
    return {'a2a_instructions': prompt}

@mcp.tool()
async def git_clone(request: GitCloneRequest, ctx: Context) -> GitCloneResponse:
    """Clone a git repository directly into the projects folder. Creates a new project and sets it as the current project."""
    # Extract project name from repository URL if not provided
    if not request.project_name:
        # Get the repository name from the URL (remove .git extension if present)
        repo_name = request.repository_url.split('/')[-1]
        if repo_name.endswith('.git'):
            repo_name = repo_name[:-4]
        project_name = repo_name
    else:
        project_name = request.project_name
    
    # Check if project already exists
    project_dir = ROOT_FOLDER / project_name
    if project_dir.exists():
        raise FileExistsError(f"Project '{project_name}' already exists.")
    
    # Build the git clone command
    cmd = ["git", "clone"]
    
    # Add optional parameters if provided
    if request.branch:
        cmd.extend(["--branch", request.branch])
    if request.depth:
        cmd.extend(["--depth", str(request.depth)])
    
    # Add repository URL and destination path
    cmd.append(request.repository_url)
    cmd.append(str(project_dir))
    
    try:
        # Execute the git clone command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        output = result.stdout + result.stderr
        
        # Initialize variables file if clone was successful
        (project_dir / ".variables.json").write_text(json.dumps({}))
        
        # Set as current project
        ctx.request_context.lifespan_context.current_project = project_name
        logger.info(f"Cloned repository to project: {project_name}")
        
        return GitCloneResponse(
            project_name=project_name,
            path=str(project_dir.relative_to(ROOT_FOLDER)),
            output=output
        )
    except subprocess.CalledProcessError as e:
        # If clone fails, return the error output
        output = e.stdout + e.stderr
        raise RuntimeError(f"Git clone failed: {output}")

@mcp.tool()
async def git(request: GitToolRequest, ctx: Context) -> GitToolResponse:
    """Run git commands in the context of the current project. Allows remote for origin management, branches, commits, pulls and pushes."""
    proj_dir = _get_project_dir(ctx)
    cmd = ["git", request.command]
    
    # Handle different git commands with specific parameters
    if request.command == 'commit':
        if not request.message:
            raise ValueError("Commit message is required for 'commit' command")
        cmd += ['-m', request.message]
    elif request.command == 'remote':
        if request.args and request.args[0] == 'add':
            if not request.remote_name or not request.remote_url:
                raise ValueError("Remote name and URL are required for 'remote add' command")
            cmd += ['add', request.remote_name, request.remote_url]
        elif not request.args:
            cmd += ['-v']  # List remotes by default
    elif request.command in ['pull', 'push']:
        if request.remote_name:
            cmd.append(request.remote_name)
        if request.branch:
            cmd.append(request.branch)
    
    # Add any additional arguments if provided
    if request.args and not (request.command == 'remote' and request.args[0] == 'add'):
        cmd += request.args
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(proj_dir),
            capture_output=True,
            text=True,
            check=True
        )
        output = result.stdout + result.stderr
    except subprocess.CalledProcessError as e:
        output = e.stdout + e.stderr
    return GitToolResponse(output=output)

# ---------------------------
# Server Entry Point
# ---------------------------
def main():
    mcp.run()
    
if __name__ == "__main__":
    main()