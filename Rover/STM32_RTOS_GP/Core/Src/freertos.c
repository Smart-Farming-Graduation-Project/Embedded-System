/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * File Name          : freertos.c
  * Description        : Code for freertos applications
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2025 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */

/* Includes ------------------------------------------------------------------*/
#include "FreeRTOS.h"
#include "task.h"
#include "main.h"
#include "cmsis_os.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include "usart.h"
#include "ultrasonic.h"
#include "motor.h"
#include "bootloader.h"
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */

/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/
/* USER CODE BEGIN Variables */
extern TIM_HandleTypeDef htim2;
/* USER CODE END Variables */
/* Definitions for Ultrasonic_Task */
osThreadId_t Ultrasonic_TaskHandle;
const osThreadAttr_t Ultrasonic_Task_attributes = {
  .name = "Ultrasonic_Task",
  .stack_size = 1024 * 4,
  .priority = (osPriority_t) osPriorityNormal,
};
/* Definitions for Rover_Commands */
osThreadId_t Rover_CommandsHandle;
const osThreadAttr_t Rover_Commands_attributes = {
  .name = "Rover_Commands",
  .stack_size = 1024 * 4,
  .priority = (osPriority_t) osPriorityAboveNormal,
};
/* Definitions for UltrasonicDistance */
osMessageQueueId_t UltrasonicDistanceHandle;
const osMessageQueueAttr_t UltrasonicDistance_attributes = {
  .name = "UltrasonicDistance"
};
/* Definitions for USReading */
osSemaphoreId_t USReadingHandle;
const osSemaphoreAttr_t USReading_attributes = {
  .name = "USReading"
};

/* Private function prototypes -----------------------------------------------*/
/* USER CODE BEGIN FunctionPrototypes */

/* USER CODE END FunctionPrototypes */

void UltrasonicTask(void *argument);
void RoverCommands(void *argument);

void MX_FREERTOS_Init(void); /* (MISRA C 2004 rule 8.1) */

/**
  * @brief  FreeRTOS initialization
  * @param  None
  * @retval None
  */
void MX_FREERTOS_Init(void) {
  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  /* USER CODE BEGIN RTOS_MUTEX */
  /* add mutexes, ... */
  /* USER CODE END RTOS_MUTEX */

  /* Create the semaphores(s) */
  /* creation of USReading */
  USReadingHandle = osSemaphoreNew(1, 1, &USReading_attributes);

  /* USER CODE BEGIN RTOS_SEMAPHORES */
  /* add semaphores, ... */
  /* USER CODE END RTOS_SEMAPHORES */

  /* USER CODE BEGIN RTOS_TIMERS */
  /* start timers, add new ones, ... */
  /* USER CODE END RTOS_TIMERS */

  /* Create the queue(s) */
  /* creation of UltrasonicDistance */
  UltrasonicDistanceHandle = osMessageQueueNew (1, sizeof(uint16_t), &UltrasonicDistance_attributes);

  /* USER CODE BEGIN RTOS_QUEUES */
  /* add queues, ... */
  /* USER CODE END RTOS_QUEUES */

  /* Create the thread(s) */
  /* creation of Ultrasonic_Task */
  Ultrasonic_TaskHandle = osThreadNew(UltrasonicTask, NULL, &Ultrasonic_Task_attributes);

  /* creation of Rover_Commands */
  Rover_CommandsHandle = osThreadNew(RoverCommands, NULL, &Rover_Commands_attributes);

  /* USER CODE BEGIN RTOS_THREADS */
  /* add threads, ... */
  /* USER CODE END RTOS_THREADS */

  /* USER CODE BEGIN RTOS_EVENTS */
  /* add events, ... */
  /* USER CODE END RTOS_EVENTS */

}

/* USER CODE BEGIN Header_UltrasonicTask */
/**
  * @brief  Function implementing the Ultrasonic_Task thread.
  * @param  argument: Not used
  * @retval None
  */
/* USER CODE END Header_UltrasonicTask */
void UltrasonicTask(void *argument)
{
  /* USER CODE BEGIN UltrasonicTask */
	HAL_TIM_IC_Start_IT(&htim2, TIM_CHANNEL_3);

  /* Infinite loop */
  for(;;)
  {
	if(osOK == osSemaphoreAcquire(USReadingHandle, 0))
	{
		// Send Trigger
		HAL_GPIO_WritePin(ULTRASONUC_TRIGGER_PORT, ULTRASONIC_TRIGGER_PIN, GPIO_PIN_SET);
		// 10us delay
		__HAL_TIM_SET_COUNTER(ULTRASONIC_ECHO_PIN_IC, 0);
		while(__HAL_TIM_GET_COUNTER(ULTRASONIC_ECHO_PIN_IC) < 10); /* TIMER Tick time = 1us */
		HAL_GPIO_WritePin(ULTRASONUC_TRIGGER_PORT, ULTRASONIC_TRIGGER_PIN, GPIO_PIN_RESET);
		__HAL_TIM_ENABLE_IT(ULTRASONIC_ECHO_PIN_IC, TIM_IT_CC3);

		// toggle at start of new reading
		HAL_GPIO_TogglePin(GPIOC, GPIO_PIN_13);
	}

    osDelay(30);
  }
  /* USER CODE END UltrasonicTask */
}

/* USER CODE BEGIN Header_RoverCommands */
/**
* @brief Function implementing the Rover_Commands thread.
* @param argument: Not used
* @retval None
*/
/* USER CODE END Header_RoverCommands */
void RoverCommands(void *argument)
{
  /* USER CODE BEGIN RoverCommands */
  uint16_t distance = 0;
  uint8_t bt_value = 0, last_bt_value = 0;
  Rover_Initialize();
  /* Infinite loop */
  for(;;)
  {
	HAL_UART_Receive(&huart1, (uint8_t*)&bt_value, 1, 0);
	if(bt_value && 'K' != bt_value) // ignore keep alive command
	{
	  if('U' == bt_value){
		  bt_value = 0;
		  Bootloader_Handle_Command();
	  }
	  else if('F' == bt_value || 'B' == bt_value || 'R' == bt_value || 'L' == bt_value)
		  last_bt_value = bt_value;
	  else
		  last_bt_value = 0;
	}
	else{ bt_value = last_bt_value; }

	switch(bt_value)
	{
	  case 'F':
		  osMessageQueueGet(UltrasonicDistanceHandle, &distance, (uint8_t*)1, 0);
		  if(20 > distance && 0 < distance)
			  Rover_Stop();
		  else
			  Rover_Forward();
		  break;

	  case 'B':
		  Rover_Backward();
		  break;

	  case 'R':
		  Rover_Right();
		  break;

	  case 'L':
		  Rover_Left();
		  break;

	  case 'S':
		  Rover_Stop();
		  break;

	  case '1': case '2': case '3': case '4': case '5':
		  Rover_Change_Speed((bt_value - '0') * 20);
		  bt_value = 0;
		  break;
	}
    osDelay(20);
  }
  /* USER CODE END RoverCommands */
}

/* Private application code --------------------------------------------------*/
/* USER CODE BEGIN Application */

/* USER CODE END Application */

