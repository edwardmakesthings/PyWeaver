"""MkDocs hooks for PyWeaver documentation.

This module contains hooks that MkDocs will run during the documentation build process.
It ensures that API reference documentation is automatically generated whenever the
documentation is built or served.

The main hook (on_pre_build) runs before MkDocs starts building the site, executing
our gen_ref_pages script to create up-to-date API documentation.

Path: docs/hooks.py
"""

import os
import logging
from pathlib import Path

def on_pre_build(config):
    """Run before MkDocs builds the documentation.

    This hook runs gen_ref_pages.py to generate API documentation before
    the site is built. This ensures the API docs are always current with
    the source code.

    Args:
        config: The MkDocs configuration dictionary containing settings
               like docs_dir, site_dir, etc.
    """
    # Get the docs directory from MkDocs config
    docs_dir = Path(config["docs_dir"])
    gen_ref_script = docs_dir / "gen_ref_pages.py"

    if gen_ref_script.exists():
        logging.info("Generating API reference documentation...")
        # Store current directory to restore it later
        original_cwd = os.getcwd()

        try:
            # Change to docs directory for relative paths to work correctly
            os.chdir(docs_dir)

            # Execute the gen_ref_pages script
            with open(gen_ref_script) as f:
                exec(f.read())

            logging.info("API reference documentation generated successfully")

        except Exception as e:
            # Log any errors but don't stop the build
            logging.error(f"Error generating API reference documentation: {e}")

        finally:
            # Always restore the original working directory
            os.chdir(original_cwd)
    else:
        logging.warning("gen_ref_pages.py not found in docs directory")