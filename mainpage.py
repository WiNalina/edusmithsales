from app import create_app, db
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler #Add the scheduler
from app.db_update.update_to_db import update_and_add_streak_info, delete_preview_files
from app.models import User, Role

app = create_app()

with app.app_context():
    sched = BackgroundScheduler(daemon=True, executors={'threadpool': ThreadPoolExecutor(max_workers=1)})
    sched.add_job(update_and_add_streak_info, 'interval', executor='threadpool', kwargs={'app':app}, minutes=5) #Update and add the information from Streak
    sched.add_job(delete_preview_files,'interval', executor='threadpool', days=1) #Delete preview files
    sched.start()
    

@app.shell_context_processor
def make_shell_context():
    return {'app':app, 'db': db, 'User': User, 'Role': Role}
