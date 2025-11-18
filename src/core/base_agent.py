"""
Base agent class for the literature review system.

Provides common functionality for all agents including configuration
access, logging, error handling, and coordination capabilities.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import time
import uuid

from .config import get_config
from ..utils.logger import get_logger, TaskLogger
from ..utils.exceptions import LiteratureReviewError, create_error_context


@dataclass
class AgentStatus:
    """Status information for an agent."""
    name: str
    state: str  # 'idle', 'running', 'completed', 'error'
    progress: float = 0.0  # 0.0 to 1.0
    current_task: Optional[str] = None
    processed_items: int = 0
    total_items: int = 0
    errors: List[str] = field(default_factory=list)
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResult:
    """Result of an agent task."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0


class BaseAgent(ABC):
    """
    Base class for all literature review agents.
    
    Provides common functionality:
    - Configuration management
    - Logging and task-specific loggers
    - Status tracking and progress reporting
    - Error handling and recovery
    - Task coordination and execution
    """
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.agent_id = str(uuid.uuid4())
        
        # Core components
        self.config = get_config()
        self.logger = get_logger(f"agent.{name}")
        self.status = AgentStatus(name=name, state='idle')
        
        # Task management
        self.current_task_id: Optional[str] = None
        self.task_logger: Optional[TaskLogger] = None
        self.execution_history: List[TaskResult] = []
        
        # Performance metrics
        self.total_execution_time = 0.0
        self.total_tasks_completed = 0
        self.total_errors = 0
    
    def create_task(self, task_name: str) -> str:
        """
        Create a new task context for logging and tracking.
        
        Args:
            task_name: Human-readable task name
            
        Returns:
            Task ID for tracking
        """
        task_id = str(uuid.uuid4())
        self.current_task_id = task_id
        self.task_logger = self.logger.create_task_logger(task_id, task_name)
        self.task_logger.info(f"Started task: {task_name}")
        return task_id
    
    def complete_task(self, task_id: str, result: TaskResult):
        """
        Complete a task and record the result.
        
        Args:
            task_id: Task ID to complete
            result: Task execution result
        """
        if self.task_logger:
            status = "completed" if result.success else "failed"
            self.task_logger.info(f"Task {status}: {result.error or 'Success'}")
        
        self.execution_history.append(result)
        self.total_tasks_completed += 1
        
        if not result.success:
            self.total_errors += 1
            self.status.errors.append(result.error or "Unknown error")
        
        self.current_task_id = None
        self.task_logger = None
    
    def update_progress(self, current: int, total: int, message: str = ""):
        """
        Update agent progress.
        
        Args:
            current: Current progress count
            total: Total items to process
            message: Optional progress message
        """
        self.status.processed_items = current
        self.status.total_items = total
        self.status.progress = current / total if total > 0 else 0.0
        
        if self.task_logger:
            self.task_logger.log_stage_progress(self.name, current, total, message)
    
    def set_status(self, state: str, current_task: Optional[str] = None):
        """
        Update agent status.
        
        Args:
            state: New state ('idle', 'running', 'completed', 'error')
            current_task: Current task description
        """
        self.status.state = state
        self.status.current_task = current_task
        
        if state == 'running' and not self.status.start_time:
            self.status.start_time = time.time()
        elif state in ['completed', 'error'] and not self.status.end_time:
            self.status.end_time = time.time()
            self.total_execution_time += self.status.end_time - self.status.start_time
    
    def execute_with_error_handling(self, task_name: str, func, *args, **kwargs) -> TaskResult:
        """
        Execute a function with comprehensive error handling.
        
        Args:
            task_name: Name of the task for logging
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            TaskResult with execution outcome
        """
        task_id = self.create_task(task_name)
        start_time = time.time()
        
        try:
            self.set_status('running', task_name)
            self.logger.info(f"Starting {task_name}")
            
            # Execute the function
            result_data = func(*args, **kwargs)
            
            execution_time = time.time() - start_time
            task_result = TaskResult(
                success=True,
                data=result_data,
                execution_time=execution_time,
                metadata={'task_id': task_id}
            )
            
            self.complete_task(task_id, task_result)
            self.set_status('completed')
            
            self.logger.info(f"Completed {task_name} in {execution_time:.2f}s")
            return task_result
            
        except LiteratureReviewError as e:
            execution_time = time.time() - start_time
            error_context = create_error_context(e, task_name=task_name, agent=self.name)
            
            task_result = TaskResult(
                success=False,
                error=str(e),
                execution_time=execution_time,
                metadata={'task_id': task_id, 'error_context': error_context}
            )
            
            self.complete_task(task_id, task_result)
            self.set_status('error')
            
            self.logger.log_error_with_context(e, error_context)
            return task_result
            
        except Exception as e:
            execution_time = time.time() - start_time
            wrapped_error = LiteratureReviewError(f"Unexpected error in {task_name}: {str(e)}")
            error_context = create_error_context(wrapped_error, task_name=task_name, agent=self.name)
            
            task_result = TaskResult(
                success=False,
                error=str(wrapped_error),
                execution_time=execution_time,
                metadata={'task_id': task_id, 'error_context': error_context}
            )
            
            self.complete_task(task_id, task_result)
            self.set_status('error')
            
            self.logger.log_error_with_context(wrapped_error, error_context)
            return task_result
    
    @abstractmethod
    def run(self, *args, **kwargs) -> TaskResult:
        """
        Main execution method for the agent.
        
        Must be implemented by all concrete agents.
        
        Returns:
            TaskResult with execution outcome
        """
        pass
    
    def validate_input(self, data: Any, schema: Dict[str, Any]) -> bool:
        """
        Validate input data against a schema.
        
        Args:
            data: Data to validate
            schema: Validation schema
            
        Returns:
            True if valid, raises exception if invalid
        """
        # Simple validation - can be extended with jsonschema
        required_fields = schema.get('required', [])
        
        if isinstance(data, dict):
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")
        
        return True
    
    def get_status_summary(self) -> Dict[str, Any]:
        """
        Get a comprehensive status summary.
        
        Returns:
            Dictionary with status information
        """
        return {
            'agent_id': self.agent_id,
            'name': self.name,
            'description': self.description,
            'status': {
                'state': self.status.state,
                'progress': self.status.progress,
                'current_task': self.status.current_task,
                'processed_items': self.status.processed_items,
                'total_items': self.status.total_items,
                'error_count': len(self.status.errors)
            },
            'performance': {
                'total_tasks_completed': self.total_tasks_completed,
                'total_errors': self.total_errors,
                'success_rate': self.total_tasks_completed / max(1, self.total_tasks_completed + self.total_errors),
                'total_execution_time': self.total_execution_time
            },
            'execution_history_size': len(self.execution_history)
        }
    
    def reset(self):
        """Reset agent state for new execution."""
        self.status = AgentStatus(name=self.name, state='idle')
        self.current_task_id = None
        self.task_logger = None
        self.execution_history = []
        self.total_execution_time = 0.0
        self.total_tasks_completed = 0
        self.total_errors = 0
        
        self.logger.info(f"Agent {self.name} has been reset")


class SequentialAgent(BaseAgent):
    """
    Agent that executes tasks sequentially in a defined order.
    
    Useful for complex workflows with multiple steps.
    """
    
    def __init__(self, name: str, description: str = ""):
        super().__init__(name, description)
        self.task_sequence: List[str] = []
        self.task_results: Dict[str, TaskResult] = {}
    
    def add_task(self, task_name: str, task_func, *args, **kwargs):
        """
        Add a task to the execution sequence.
        
        Args:
            task_name: Name of the task
            task_func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
        """
        self.task_sequence.append({
            'name': task_name,
            'func': task_func,
            'args': args,
            'kwargs': kwargs
        })
    
    def run(self, *args, **kwargs) -> TaskResult:
        """
        Execute all tasks in sequence.
        
        Returns:
            TaskResult with overall execution outcome
        """
        if not self.task_sequence:
            return TaskResult(
                success=False,
                error="No tasks defined for execution"
            )
        
        self.logger.info(f"Starting sequential execution of {len(self.task_sequence)} tasks")
        
        for i, task in enumerate(self.task_sequence):
            self.update_progress(i, len(self.task_sequence), f"Executing: {task['name']}")
            
            result = self.execute_with_error_handling(
                task['name'],
                task['func'],
                *task['args'],
                **task['kwargs']
            )
            
            self.task_results[task['name']] = result
            
            if not result.success:
                # Stop execution on failure
                self.logger.error(f"Sequential execution stopped at task: {task['name']}")
                return result
        
        # All tasks completed successfully
        self.update_progress(len(self.task_sequence), len(self.task_sequence), "All tasks completed")
        
        return TaskResult(
            success=True,
            data=self.task_results,
            metadata={'completed_tasks': list(self.task_results.keys())}
        )
    
    def get_task_result(self, task_name: str) -> Optional[TaskResult]:
        """Get result of a specific task."""
        return self.task_results.get(task_name)


class ParallelAgent(BaseAgent):
    """
    Agent that can execute tasks in parallel.
    
    Useful for independent operations that can run concurrently.
    """
    
    def __init__(self, name: str, description: str = ""):
        super().__init__(name, description)
        self.max_workers = self.config.get('parallel.max_workers', 4)
    
    async def run_parallel(self, tasks: List[Dict[str, Any]]) -> List[TaskResult]:
        """
        Execute multiple tasks in parallel.
        
        Args:
            tasks: List of task dictionaries with 'name', 'func', 'args', 'kwargs'
            
        Returns:
            List of TaskResult objects
        """
        import asyncio
        
        async def execute_task(task):
            return self.execute_with_error_handling(
                task['name'],
                task['func'],
                *task['args'],
                **task['kwargs']
            )
        
        # Execute all tasks concurrently
        results = await asyncio.gather(
            *[execute_task(task) for task in tasks],
            return_exceptions=True
        )
        
        return results
    
    def run(self, *args, **kwargs) -> TaskResult:
        """
        Execute tasks in parallel.
        
        Note: This is a synchronous wrapper around the async implementation.
        Concrete implementations should override run_parallel directly.
        """
        import asyncio
        
        tasks = kwargs.get('tasks', [])
        if not tasks:
            return TaskResult(
                success=False,
                error="No tasks provided for parallel execution"
            )
        
        try:
            results = asyncio.run(self.run_parallel(tasks))
            
            return TaskResult(
                success=True,
                data=results,
                metadata={'total_tasks': len(tasks)}
            )
            
        except Exception as e:
            return TaskResult(
                success=False,
                error=f"Parallel execution failed: {str(e)}"
            )