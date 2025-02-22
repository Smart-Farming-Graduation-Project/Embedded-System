/*
 * ultrasonic.c
 *
 *  Created on: Feb 21, 2025
 *      Author: Ehab
 */



#include "ultrasonic.h"

extern TIM_HandleTypeDef htim2;
extern uint16_t distance;
extern uint8_t isReadingFinished;
static volatile uint8_t isRisingCaptured = 0;
static volatile uint32_t IC_Value1 = 0;
static volatile uint32_t IC_Value2 = 0;
static volatile uint32_t IC_Difference = 0;



static void Delay_10US(void)
{
	__HAL_TIM_SET_COUNTER(ULTRASONIC_ECHO_PIN_IC, 0);
	/* TIMER Tick time = 1us */
	while(__HAL_TIM_GET_COUNTER(ULTRASONIC_ECHO_PIN_IC) < 10);
}

void Ultrasnoic_Initialize(void)
{
	HAL_TIM_IC_Start_IT(&htim2, TIM_CHANNEL_3);
	Ultrasonic_Get_Distance();
	HAL_Delay(100);
}

void Ultrasonic_Get_Distance(void)
{
	/* Send Trigger Signal to the Ultrasonic Trigger Pin */
	HAL_GPIO_WritePin(ULTRASONUC_TRIGGER_PORT, ULTRASONIC_TRIGGER_PIN, GPIO_PIN_SET);
	Delay_10US();
	HAL_GPIO_WritePin(ULTRASONUC_TRIGGER_PORT, ULTRASONIC_TRIGGER_PIN, GPIO_PIN_RESET);

	__HAL_TIM_ENABLE_IT(ULTRASONIC_ECHO_PIN_IC, TIM_IT_CC3);
}

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

		isReadingFinished = 1;

		isRisingCaptured = 0;
		__HAL_TIM_SET_CAPTUREPOLARITY(htim, TIM_CHANNEL_3, TIM_INPUTCHANNELPOLARITY_RISING);
		__HAL_TIM_DISABLE_IT(&htim2, TIM_IT_CC3);
	}
	else{ /* Nothing */ }
}
