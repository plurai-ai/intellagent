# Architecture Guide
<img src="./arch_overview.png" alt="Architecture overview" width="70%">

This document outlines the system design of Chat-Agent-Simulator, which is built around four primary components: Event Generation, Dialog Management, Simulation Execution, and Results Analysis.

## System Design

### 1. Event Generation
The Event Generation system consists of two main components:

- **Description Generator**: Generates structured descriptions of events using LLM-based policies and guidelines.
  - Builds a policy graph to maintain relationships between different policies
  - Handles policy extraction and scoring
  - Reference: `simulator/descriptor_generator.py`

- **Events Generator**: Converts descriptions into actionable events
  - Manages database operations and event validation
  - Handles parallel event processing
  - Reference: `simulator/events_generator.py`

### 2. Dialog Management
The Dialog Management system orchestrates conversations between simulated users and chatbots:

- **Dialog Graph**: Implements a state machine for conversation flow
  - Manages message passing between user and chatbot
  - Handles conversation termination conditions
  - Reference: `simulator/dialog_graph.py`

- **Dialog Manager**: Controls the execution of dialogs
  - Configures LLM models for both user and chatbot
  - Manages parallel dialog execution
  - Reference: `simulator/dialog_manager.py`

### 3. Simulation Execution
The Simulation Executor coordinates the entire simulation process:

- **Environment Setup**: Manages configuration and resources
  - Loads prompts, tools, and databases
  - Configures LLM settings
  - Reference: `simulator/env.py`

- **Execution Flow**: Handles the simulation lifecycle
  - Coordinates between components
  - Manages batch processing
  - Reference: `simulator/simulator_executor.py`

### 4. Results Analysis and Visualization
The system includes comprehensive analysis and visualization tools:

- **Analytics**: Tracks and analyzes simulation metrics
  - Monitors costs and performance
  - Generates success/failure statistics
  - Reference: `simulator/healthcare_analytics.py`

- **Visualization**: Provides interactive dashboards
  - Experiments reporting
  - Session visualization
  - Reference: `simulator/visualization/`

## Design Considerations

### 1. Scalability
- **Parallel Processing**: The system implements batch processing and parallel execution patterns for handling multiple simulations simultaneously.
- **Modular Architecture**: Components are designed to be independent and easily scalable.

### 2. Extensibility
- **Plugin System**: Tools and validators can be dynamically loaded and configured
- **Configurable Components**: Most components accept configuration dictionaries for easy modification

### 3. Monitoring and Debugging
- **Comprehensive Logging**: Structured logging system with different severity levels
  
- **Analytics Events**: Tracking system for monitoring performance and errors
  
### 4. Cost Management
- **Cost Tracking**: Built-in cost monitoring for LLM usage
- **Batch Processing**: Optimized processing to minimize API calls
- **Caching**: Implementation of caching strategies for expensive operations

### 5. Error Handling
- **Graceful Degradation**: System continues functioning even if some components fail
- **Error Tracking**: Comprehensive error tracking and reporting system
  
### 6. Security
- **Environment Configuration**: Sensitive configuration managed through environment variables
- **Input Validation**: Structured validation of inputs and outputs
- **Database Security**: Proper handling of database connections and queries

This architecture provides a robust foundation for simulating and analyzing chat agent interactions while maintaining flexibility for future extensions and modifications.

