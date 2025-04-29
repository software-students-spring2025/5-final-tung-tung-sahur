import pytest
from unittest.mock import patch, MagicMock
import app
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.background import BackgroundScheduler


class TestScheduler:
    @patch("app.BackgroundScheduler")
    def test_scheduler_initialization(self, mock_scheduler_class):
        # Setup
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler
        
        # Execute by re-initializing the scheduler
        app.scheduler = None
        app.scheduler = BackgroundScheduler(timezone="UTC", daemon=True)
        app.scheduler.add_job(
            app.due_soon_job,
            trigger=app.IntervalTrigger(minutes=1),
            next_run_time=datetime.now(timezone.utc),
            id="due_reminder",
        )
        app.scheduler.start()
        
        # Assert
        mock_scheduler.add_job.assert_called_once()
        mock_scheduler.start.assert_called_once()