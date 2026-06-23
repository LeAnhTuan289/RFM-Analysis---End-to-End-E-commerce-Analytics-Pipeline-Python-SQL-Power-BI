"""
Main entry point for ETL Pipeline.

Flow:
------
1. Load environment variables
2. Initialize orchestrator
3. Execute ETL pipeline
4. Log execution summary
"""

import sys
import time
import traceback

from utils.config import load_env_variables
from orchestration.pipeline_orchestrator import PipelineOrchestrator
from utils.logger import setup_logger


def main() -> None:
    """
    Main ETL execution function.
    """

    logger = setup_logger(__name__)

    start_time = time.time()

    try:
        logger.info("\n")
        logger.info("=" * 40)
        logger.info("STARTING ETL PIPELINE")
        logger.info("=" * 40)

        # Load environment variables
        load_env_variables()

        logger.info("Environment variables loaded successfully")

        # Initialize orchestrator
        orchestrator = PipelineOrchestrator()

        logger.info("Pipeline orchestrator initialized")

        # Execute pipeline
        orchestrator.run()

        # Success summary
        elapsed_time = time.time() - start_time

        logger.info("\n")
        logger.info("=" * 40)
        logger.info("ETL PIPELINE COMPLETED SUCCESSFULLY")
        logger.info(f"Total Runtime: {elapsed_time:.2f} seconds")
        logger.info("=" * 40)

        sys.exit(0)

    except KeyboardInterrupt:

        elapsed_time = time.time() - start_time

        logger.warning("Pipeline execution interrupted by user")
        logger.warning(f"Runtime before interruption: {elapsed_time:.2f} seconds")

        sys.exit(1)

    except Exception as e:

        elapsed_time = time.time() - start_time

        logger.info("\n")
        logger.error("=" * 40)
        logger.error("ETL PIPELINE FAILED")
        logger.error(f"Error: {e}")
        logger.error(f"Runtime before failure: {elapsed_time:.2f} seconds")
        logger.error(traceback.format_exc())
        logger.error("=" * 40)

        sys.exit(1)


if __name__ == "__main__":
    main()
