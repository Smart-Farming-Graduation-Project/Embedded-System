/*
 * ultrasonic.c
 *
 *  Created on: Feb 21, 2025
 *      Author: Ehab
 */



#include "ultrasonic.h"
#include "cmsis_os.h"

extern TIM_HandleTypeDef htim2;
extern osMessageQueueId_t UltrasonicDistanceHandle;
extern osSemaphoreId_t USReadingHandle;

uint16_t distance;
static volatile uint8_t isRisingCaptured = 0;
static volatile uint32_t IC_Value1 = 0;
static volatile uint32_t IC_Value2 = 0;
static volatile uint32_t IC_Difference = 0;



void HAL_TIM_IC_CaptureCallback(TIM_HandleTypeDef *htim)
{
	/* Capture rising edge */
	if(0 == isRisingCaptured)
	{
		IC_Value1 = HAL_TIM_ReadCapturedValue(htim, TIM_CHANNEL_3);
		isRisingCaptured = 1;
		__HAL_TIM_SET_CAPTUREPOLARITY(htim, TIM_CHANNEL_3, TIM_INPUTCHANNELPOLARITY_FALLING);
	}
	/* Capture falling edge */
	else if(1 == isRisingCaptured)
	{
		IC_Value2 = HAL_TIM_ReadCapturedValue(htim, TIM_CHANNEL_3);
		__HAL_TIM_SET_COUNTER(htim, 0);

		if(IC_Value2 > IC_Value1)
		{
			IC_Difference = IC_Value2 - IC_Value1;
		}
		else if(IC_Value1 > IC_Value2)
		{
			IC_Difference = (0xFFFF - IC_Value1) + IC_Value2;
		}

		distance = IC_Difference * 0.0173;

		osMessageQueueReset(UltrasonicDistanceHandle);
		osMessageQueuePut(UltrasonicDistanceHandle, &distance, 1, 0);

		isRisingCaptured = 0;
		__HAL_TIM_SET_CAPTUREPOLARITY(htim, TIM_CHANNEL_3, TIM_INPUTCHANNELPOLARITY_RISING);
		__HAL_TIM_DISABLE_IT(&htim2, TIM_IT_CC3);

		osSemaphoreRelease(USReadingHandle);
	}
	else{ /* Nothing */ }
}
