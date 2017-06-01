import schedule
import time

import app.database
import worker.archive
import worker.scrape
import cli
from model import User


class SchedulerCli(cli.BaseCli):
    """ Runs scheduled tasks. """

    def _run(self, args, config):
        """ Main entry point. """
        # Connect to database.
        database_config = dict(config.items('database'))
        self._db = app.database.get_engine(database_config, super_user=True)
        session = app.database.get_session(self._db)

        # Get system user.
        # Required in order to request new site tests
        # when existing results expire.
        # Results are stored per-user so a system user is used to create public results.
        self.user = session.query(User).filter(User.email == 'system').one()

        self._logger.info('Scheduler started.')

        # Schedule jobs
        schedule.every().day.at('00:01').do(self._delete_expired_archives)
        schedule.every().day.at('00:02').do(self._delete_expired_results)

        # Process jobs
        while True:
            try:
                schedule.run_pending()
                time.sleep(1)
            except KeyboardInterrupt:
                self._logger.info('Stopping the scheduler.')
                return

    def _delete_expired_archives(self):
        """
        Delete archives older than expiry date.
        """
        worker.archive.delete_expired_archives.enqueue()

    def _delete_expired_results(self):
        """
        Delete results older than expiry date.
        """
        worker.scrape.delete_expired_results.enqueue(user_id=self.user.id)
