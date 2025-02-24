"""Module that facilitates the downloading of entire Bunkr albums.

This module provides features for managing progress, handling failed downloads, and
integrating with live task displays.
"""

import asyncio
from argparse import Namespace
from asyncio import Semaphore

from helpers.config import MAX_WORKERS
from helpers.crawlers.crawler_utils import get_download_info
from helpers.general_utils import fetch_page
from helpers.managers.live_manager import LiveManager

from .media_downloader import MediaDownloader


class AlbumDownloader:
    """Manage the downloading of entire Bunkr albums."""

    def __init__(
            self,
            session_info: tuple,
            album_info: tuple,
            live_manager: LiveManager,
            args: Namespace,
        ) -> None:
        """Initialize the AlbumDownloader instance."""
        self.bunkr_status, self.download_path = session_info
        self.album_id, self.item_pages = album_info
        self.live_manager = live_manager
        self.failed_downloads = []
        self.args = args

    async def execute_item_download(
            self,
            item_page: str,
            current_task: int,
            semaphore: Semaphore,
        ) -> None:
        """Handle the download of an individual item in the album."""
        async with semaphore:
            task = self.live_manager.add_task(current_task=current_task)

            # Process the download of an item
            item_soup = await fetch_page(item_page)
            (
                item_download_link,
                item_file_name,
            ) = await get_download_info(item_soup)

            # Download item
            if item_download_link:
                downloader = MediaDownloader(
                    session_info=(self.bunkr_status, self.download_path),
                    download_info=(item_download_link, item_file_name, task),
                    live_manager=self.live_manager,
                    args=self.args,
                )

                failed_download = await asyncio.to_thread(downloader.download)
                if failed_download:
                    self.failed_downloads.append(failed_download)

    async def retry_failed_download(
            self, task: int, file_name: str, download_link: str,
        ) -> None:
        """Handle failed downloads and retries them."""
        downloader = MediaDownloader(
            session_info=(self.bunkr_status, self.download_path),
            download_info=(download_link, file_name, task),
            live_manager=self.live_manager,
            retries=1,  # Retry once for failed downloads
        )
        # Run the synchronous download function in a separate thread
        await asyncio.to_thread(downloader.download)

    async def process_failed_downloads(self) -> None:
        """Process any failed downloads after the initial attempt."""
        for data in self.failed_downloads:
            await self.retry_failed_download(
                data["id"],
                data["file_name"],
                data["download_link"],
            )
        self.failed_downloads.clear()

    async def download_album(self, max_workers: int = MAX_WORKERS) -> None:
        """Handle the album download."""
        num_tasks = len(self.item_pages)
        self.live_manager.add_overall_task(
            description=self.album_id,
            num_tasks=num_tasks,
        )

        # Create tasks for downloading each item in the album
        semaphore = asyncio.Semaphore(max_workers)
        tasks = [
            self.execute_item_download(item_page, current_task, semaphore)
            for current_task, item_page in enumerate(self.item_pages)
        ]
        await asyncio.gather(*tasks)

        # If there are failed downloads, process them after all downloads are
        # complete
        if self.failed_downloads:
            await self.process_failed_downloads()
