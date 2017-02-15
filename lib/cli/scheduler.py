import schedule
import time

import worker.archive
import worker.scrape
import cli


class SchedulerCli(cli.BaseCli):
    """ Runs scheduled tasks. """

    def _run(self, args, config):
        """ Main entry point. """

        self._logger.info('Scheduler started.')

        #schedule.every().day.at('00:01').do(self._delete_expired_archives)
        #schedule.every().day.at('00:02').do(self._delete_expired_results)
        schedule.every(1).minutes.do(self._delete_expired_archives)
        schedule.every(1).minutes.do(self._delete_expired_results)

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

        worker.scrape.delete_expired_results.enqueue()
