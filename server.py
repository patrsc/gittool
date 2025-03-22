import os
import asyncio
from urllib.parse import unquote
import signal
import sys
import time
from aiohttp import web

PORT = int(sys.argv[1])

# Global variable to store the runner
runner = None
last_keepalive = time.time()
KEEPALIVE_CHECK_INTERVAL = 1
KEEPALIVE_TIMEOUT = 5

async def check_keepalive():
    """Background task to check keepalive and shut down if needed."""
    while True:
        await asyncio.sleep(KEEPALIVE_CHECK_INTERVAL)
        print("checking keepalive")
        if time.time() - last_keepalive > KEEPALIVE_TIMEOUT:
            print(f"No keepalive received for {KEEPALIVE_TIMEOUT} seconds, shutting down...")
            await runner.cleanup()
            await runner.shutdown()
            signal.raise_signal(signal.SIGTERM)

async def run_git_command(dir_path, *args):
    """Run a git command asynchronously and return its output."""
    try:
        process = await asyncio.create_subprocess_exec(
            'git', '-C', dir_path, *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            return None
        return stdout.decode().strip()
    except Exception:
        return None

async def get_unsynced_branches(dir_path):
    """Get the number of unsynced branches in the repository."""

    # Get all local branches
    branches_output = await run_git_command(dir_path, 'branch')
    if not branches_output:
        return 0
    
    branches = [b.strip().replace('* ', '') for b in branches_output.split('\n')]
    unsynced_count = 0

    for branch in branches:
        # Check if branch has a tracking branch
        tracking_branch = await run_git_command(dir_path, 'rev-parse', '--abbrev-ref', f'{branch}@{{upstream}}')
        
        if not tracking_branch:
            # Branch has no tracking branch
            unsynced_count += 1
            continue

        # Check if branch is ahead/behind
        counts = await run_git_command(dir_path, 'rev-list', '--left-right', '--count', f'{tracking_branch}...{branch}')
        if counts:
            behind, ahead = map(int, counts.split())
            if ahead > 0 or behind > 0:
                unsynced_count += 1

    return unsynced_count


async def get_git_info(dir_path):
    """Get Git repository information for a directory asynchronously."""
    try:
        # Check if directory is a git repo
        if not os.path.exists(os.path.join(dir_path, '.git')):
            return None

        # Fetch remotes first
        await run_git_command(dir_path, 'fetch', '--all', '--quiet', '--prune')

        # Get current branch
        branch = await run_git_command(dir_path, 'rev-parse', '--abbrev-ref', 'HEAD')
        if not branch:
            return None

        # Check if working directory is clean
        status = await run_git_command(dir_path, 'status', '--porcelain')
        is_clean = not status

        # Get current commit hash
        commit = await run_git_command(dir_path, 'rev-parse', '--short', 'HEAD')
        if not commit:
            return None

        # Get stash count
        stash_list = await run_git_command(dir_path, 'stash', 'list')
        stash_count = len(stash_list.split('\n')) if stash_list else 0

        # Get tracking information
        tracking_info = None
        try:
            # Get the tracking branch
            tracking_branch = await run_git_command(dir_path, 'rev-parse', '--abbrev-ref', f'{branch}@{{upstream}}')
            if tracking_branch:
                # Get ahead/behind counts
                counts = await run_git_command(dir_path, 'rev-list', '--left-right', '--count', f'{tracking_branch}...HEAD')
                if counts:
                    behind, ahead = map(int, counts.split())
                    tracking_info = {
                        "ahead": ahead,
                        "behind": behind
                    }
        except Exception:
            # No tracking branch found
            tracking_info = None

        # Get number of unsynced branches
        unsynced_branches = await get_unsynced_branches(dir_path)

        return {
            "branch": branch,
            "is_clean": is_clean,
            "commit": commit,
            "stash_count": stash_count,
            "tracking": tracking_info,
            "unsynced_branches": unsynced_branches,
        }
    except Exception:
        return None

async def list_folders(request):
    """Return a JSON list of folder names in the current directory."""
    current_directory = os.getcwd()
    folders = [name for name in os.listdir(current_directory) 
              if os.path.isdir(os.path.join(current_directory, name)) and name != 'start.app']
    return web.json_response(folders)

async def get_dir_info(request):
    """Return JSON with Git information."""
    try:
        dirname = unquote(request.match_info['dirname'])
        target_dir = os.path.join(os.getcwd(), dirname)
        
        if not os.path.isdir(target_dir):
            return web.Response(status=404, text=f"Directory '{dirname}' not found")

        # Get Git info asynchronously
        git_info = await get_git_info(target_dir)
        return web.json_response({"git": git_info})
    except Exception as e:
        return web.Response(status=500, text=str(e))

async def sync_repo(request, operation):
    """Helper function to push or pull repository changes."""
    try:
        dirname = unquote(request.match_info['dirname'])
        target_dir = os.path.join(os.getcwd(), dirname)
        result = await run_git_command(target_dir, operation)
        if result is None:
            return web.Response(status=500, text=f"Failed to {operation} changes")
        return web.json_response({"status": "success", "message": f"{operation} successful"})
    except Exception as e:
        return web.Response(status=500, text=str(e))

async def push_repo(request):
    """Push changes to the remote repository."""
    return await sync_repo(request, 'push')

async def pull_repo(request):
    """Pull changes from the remote repository."""
    return await sync_repo(request, 'pull')

async def root_handler(request):
    """Redirect root path to index.html"""
    return web.HTTPFound('/index.html')

async def keepalive_handler(request):
    """Handle keepalive requests."""
    global last_keepalive
    last_keepalive = time.time()
    print("keepalive received")
    return web.Response(text="ok")

def init_app():
    app = web.Application()
    app.router.add_get('/', root_handler)
    app.router.add_get('/list', list_folders)
    app.router.add_get('/get/{dirname}', get_dir_info)
    app.router.add_post('/push/{dirname}', push_repo)
    app.router.add_post('/pull/{dirname}', pull_repo)
    app.router.add_get('/keepalive', keepalive_handler)
    app.router.add_static('/', path=os.path.dirname(__file__))

    # Add startup signal handler
    async def startup(app):
        app['keepalive_task'] = asyncio.create_task(check_keepalive())

    app.on_startup.append(startup)
    return app

if __name__ == "__main__":
    app = init_app()
    print(f"Serving on http://localhost:{PORT}")
    runner = web.AppRunner(app)
    web.run_app(app, port=PORT)
