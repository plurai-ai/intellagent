from simulator.utils.logger_config import get_logger, ConsoleColor
from typing import Any
from langchain_core.callbacks import BaseCallbackHandler
import contextlib
from tqdm import trange, tqdm
import concurrent.futures
import asyncio
from simulator.healthcare_analytics import ExceptionEvent, track_event


def batch_invoke(llm_function, inputs: list[Any], num_workers: int, callbacks: list[BaseCallbackHandler]) -> list[Any]:
    """
    Invoke a langchain runnable function in parallel
    :param llm_function: The agent invoking function
    :param inputs: The list of all inputs
    :param num_workers: The number of workers
    :param callbacks: Langchain callbacks list
    :return: A list of results
    """
    logger = get_logger()

    def sample_generator():
        for i, sample in enumerate(inputs):
            yield i, sample

    def process_sample_with_progress(sample):
        i, sample = sample
        error = None
        with contextlib.ExitStack() as stack:
            CB = [stack.enter_context(callback()) for callback in callbacks]
            try:
                result = llm_function(sample)
            except Exception as e:
                logger.error('Error in chain invoke: {}'.format(e))
                result = None
                error = 'Error while running: ' + str(e)
                track_event(ExceptionEvent(exception_type=type(e).__name__,
                                   error_message=error))
            for cb in CB:
                accumulate_usage = cb.total_cost
        pbar.update(1)  # Update the progress bar
        return {'index': i, 'result': result, 'usage': accumulate_usage, 'error': error}

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        with tqdm(total=len(inputs), desc="Processing samples") as pbar:
            all_results = list(executor.map(process_sample_with_progress, sample_generator()))

    all_results = [res for res in all_results if res is not None]
    return all_results


async def batch_ainvoke(llm_async_function, inputs: list[Any], num_workers: int,
                        callbacks: list[BaseCallbackHandler], timeout: int = 5) -> list[Any]:
    """
    Invoke a langchain runnable function in parallel
    :param llm_async_function: The agent invoking function
    :param inputs: The list of all inputs
    :param num_workers: The number of workers
    :param callbacks: Langchain callbacks list
    :param timeout: The timeout for each task (in seconds)
    :return: A list of results
    """
    logger = get_logger()
    def sample_generator():
        for i, sample in enumerate(inputs):
            yield i, sample

    async def process_sample_with_progress(sample):
        i, sample = sample
        error = None
        with contextlib.ExitStack() as stack:
            CB = [stack.enter_context(callback()) for callback in callbacks]
            try:
                result = await llm_async_function(sample)
            except Exception as e:
                logger.error('Error in chain invoke: {}'.format(e))
                result = None
                error = 'Error while running: ' + str(e)
                track_event(ExceptionEvent(exception_type=type(e).__name__,
                                   error_message=error))
            for cb in CB:
                accumulate_usage = cb.total_cost
        return {'index': i, 'result': result, 'usage': accumulate_usage, 'error': error}

    semaphore = asyncio.Semaphore(num_workers)  # Limit to 2 workers

    # Task runner that acquires the semaphore
    async def task_runner(func_input):
        async with semaphore:
            try:
                return await asyncio.wait_for(process_sample_with_progress(func_input), timeout=timeout)
            except asyncio.TimeoutError as e:
                print(f"Task reached timeout and was terminated.")
                error_message = 'Timeout'
                track_event(ExceptionEvent(exception_type=type(e).__name__,
                                   error_message=error_message))
                return {'index': func_input[0], 'result': None, 'usage': 0,
                        'error': 'error_message'}  # Return None or any appropriate value for a failed task

    # Create tasks
    tasks = [task_runner(func_input) for func_input in sample_generator()]

    # Use tqdm to track the progress of tasks
    results = []
    for task in tqdm(asyncio.as_completed(tasks), total=len(tasks)):
        result = await task
        results.append(result)
    return results


def async_batch_invoke(llm_async_function, inputs: list[Any], num_workers: int,
                       callbacks: list[BaseCallbackHandler], timeout: int = 5) -> list[Any]:
    return asyncio.run(batch_ainvoke(llm_async_function, inputs, num_workers, callbacks, timeout))
