#http://www.apache.org/licenses/LICENSE-2.0.txt
#
#
#Copyright 2015 Intel Corporation
#
#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.

from modules import utils
from modules.logger import log
from unittest import TextTestRunner

import sys
import unittest


class FacterCollectorLargeTest(unittest.TestCase):

    def setUp(self):
        # set and download required binaries (snapd, snapctl, plugins)
        self.binaries = utils.set_binaries()
        utils.download_binaries(self.binaries)

        log.debug("Starting snapd")
        self.binaries.snapd.start()
        if not self.binaries.snapd.isAlive():
            self.fail("snapd thread died")

        log.debug("Waiting for snapd to finish starting")
        if not self.binaries.snapd.wait():
            log.error("snapd errors: {}".format(self.binaries.snapd.errors))
            self.binaries.snapd.kill()
            self.fail("snapd not ready, timeout!")

    def test_facter_collector_plugin(self):
        # load facter collector
        loaded = self.binaries.snapctl.load_plugin("snap-plugin-collector-facter")
        self.assertTrue(loaded, "facter collector loaded")

        # check available metrics, plugins and tasks
        metrics = self.binaries.snapctl.list_metrics()
        plugins = self.binaries.snapctl.list_plugins()
        tasks = self.binaries.snapctl.list_tasks()
        self.assertGreater(len(metrics), 0, "Metrics available {} expected {}".format(len(metrics), 0))
        self.assertEqual(len(plugins), 1, "Plugins available {} expected {}".format(len(plugins), 1))
        self.assertEqual(len(tasks), 0, "Tasks available {} expected {}".format(len(tasks), 0))

        # check config policy for metric
        rules = self.binaries.snapctl.metric_get("/intel/facter/id")
        self.assertEqual(len(rules), 1, "Rules available {} expected {}".format(len(rules), 1))

        # create and list available task
        task_id = self.binaries.snapctl.create_task("/snap-plugin-collector-facter/scripts/docker/large/task.json")
        tasks = self.binaries.snapctl.list_tasks()
        self.assertEqual(len(tasks), 1, "Tasks available {} expected {}".format(len(tasks), 1))

        # check if task hits and fails
        hits = self.binaries.snapctl.task_hits_count(task_id)
        fails = self.binaries.snapctl.task_fails_count(task_id)
        self.assertGreater(hits, 0, "Task hits {} expected {}".format(hits, ">0"))
        self.assertEqual(fails, 0, "Task fails {} expected {}".format(fails, 0))

        # stop task and list available tasks
        stopped = self.binaries.snapctl.stop_task(task_id)
        self.assertTrue(stopped, "Task stopped")
        tasks = self.binaries.snapctl.list_tasks()
        self.assertEqual(len(tasks), 1, "Tasks available {} expected {}".format(len(tasks), 1))

        # unload plugin, list metrics and plugins
        self.binaries.snapctl.unload_plugin("collector", "facter", "8")
        metrics = self.binaries.snapctl.list_metrics()
        plugins = self.binaries.snapctl.list_plugins()
        self.assertEqual(len(metrics), 0, "Metrics available {} expected {}".format(len(metrics), 0))
        self.assertEqual(len(plugins), 0, "Plugins available {} expected {}".format(len(plugins), 0))

        # check for snapd errors
        self.assertEqual(len(self.binaries.snapd.errors), 0, "Errors found during snapd execution")

    def tearDown(self):
        log.debug("Stopping snapd thread")
        self.binaries.snapd.stop()
        if self.binaries.snapd.isAlive():
            log.warn("snapd thread did not died")

if __name__ == "__main__":
    test_suite = unittest.TestLoader().loadTestsFromTestCase(FacterCollectorLargeTest)
    test_result = TextTestRunner().run(test_suite)
    # exit with return code equal to number of failures
    sys.exit(len(test_result.failures))
