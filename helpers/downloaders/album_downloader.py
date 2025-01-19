"""
The `album_downloader` module facilitates the downloading of entire Bunkr
albums, providing features for managing progress, handling failed downloads,
and integrating with live task displays.
"""

import asyncio

from helpers.crawlers.crawler_utils import get_download_info

from helpers.general_utils import fetch_page

from .media_downloader import MediaDownloader

class AlbumDownloader:
    """
    Manages the downloading of entire Bunkr albums, including tracking progress
    and handling failed downloads.

    Attributes:
        bunkr_status (dict): Status of Bunkr subdomains.
        download_path (str): Directory where the album will be saved.
        album_id (str): ID of the album being downloaded.
        item_pages (list): List of item pages in the album.
        live_manager (LiveManager): Handles live display of progress and logs.
        failed_downloads (list): List of downloads that failed during the
                                 process.
    """

    def __init__(self, session_info, album_info, live_manager, ignore_list):
        self.bunkr_status, self.download_path = session_info
        self.album_id, self.item_pages = album_info
        self.live_manager = live_manager
        self.failed_downloads = []
        self.ignore_list = ignore_list

    async def execute_item_download(self, item_page, current_task, semaphore):
        """Handles the download of an individual item in the album."""
        async with semaphore:
            task = self.live_manager.add_task(current_task=current_task)

            # Process the download of an item
            item_soup = await fetch_page(item_page)
            (
                item_download_link,
                item_file_name
            ) = await get_download_info(item_soup)

            # Download item
            if item_download_link:
                downloader = MediaDownloader(
                    session_info=(self.bunkr_status, self.download_path),
                    download_info=(item_download_link, item_file_name, task),
                    live_manager=self.live_manager,
                    ignore_list=self.ignore_list
                )

                failed_download = await asyncio.to_thread(downloader.download)
                if failed_download:
                    self.failed_downloads.append(failed_download)

    async def retry_failed_download(self, task, file_name, download_link):
        """Handles failed downloads and retries them."""
        downloader = MediaDownloader(
            session_info=(self.bunkr_status, self.download_path),
            download_info=(download_link, file_name, task),
            live_manager=self.live_manager,
            retries=1  # Retry once for failed downloads
        )
        # Run the synchronous download function in a separate thread
        await asyncio.to_thread(downloader.download)

    async def process_failed_downloads(self):
        """Processes any failed downloads after the initial attempt."""
        for data in self.failed_downloads:
            await self.retry_failed_download(
                data['id'],
                data['file_name'],
                data['download_link']
            )
        self.failed_downloads.clear()

    async def download_album(self, max_workers=5):
        """Main method to handle the album download."""
        num_tasks = len(self.item_pages)
        self.live_manager.add_overall_task(
            description=self.album_id,
            num_tasks=num_tasks
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
