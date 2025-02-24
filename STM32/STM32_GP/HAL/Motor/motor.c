/*****************************************************************************************
 ****************** @file           : motor.c		         	      ********************
 ****************** @author         : Ehab Magdy Abdallah             ********************
 ****************** @brief          : interface file DC Motor         ********************
******************************************************************************************/

#include "motor.h"

static void Set_Speed(void);
static void adjust_PWM_dutyCycle(TIM_HandleTypeDef* pwmHandle, uint32_t pwmChannel, float dutyCycle);

uint8_t lastSpeed = 0;
uint8_t speed = 0;

/******************************      Software interfaces     ******************************/
void Rover_Initialize(void)
{
	speed = 0;
	lastSpeed = speed;
	Set_Speed();
	HAL_TIM_PWM_Start(MOTOR_PWM_TIMER, TIM_CHANNEL_1);
	HAL_TIM_PWM_Start(MOTOR_PWM_TIMER, TIM_CHANNEL_2);
	HAL_TIM_PWM_Start(MOTOR_PWM_TIMER, TIM_CHANNEL_3);
	HAL_TIM_PWM_Start(MOTOR_PWM_TIMER, TIM_CHANNEL_4);
}

void Rover_Forward(void)
{
	HAL_GPIO_WritePin(MOTOR_PORT, MOTOR_LEFT_FRONT_PIN, GPIO_PIN_SET);
	HAL_GPIO_WritePin(MOTOR_PORT, MOTOR_RIGHT_FRONT_PIN, GPIO_PIN_SET);
	HAL_GPIO_WritePin(MOTOR_PORT, MOTOR_LEFT_BACK_PIN, GPIO_PIN_SET);
	HAL_GPIO_WritePin(MOTOR_PORT, MOTOR_RIGHT_BACK_PIN, GPIO_PIN_SET);
	Set_Speed();

}

void Rover_Backward(void)
{
	HAL_GPIO_WritePin(MOTOR_PORT, MOTOR_LEFT_FRONT_PIN, GPIO_PIN_RESET);
	HAL_GPIO_WritePin(MOTOR_PORT, MOTOR_RIGHT_FRONT_PIN, GPIO_PIN_RESET);
	HAL_GPIO_WritePin(MOTOR_PORT, MOTOR_LEFT_BACK_PIN, GPIO_PIN_RESET);
	HAL_GPIO_WritePin(MOTOR_PORT, MOTOR_RIGHT_BACK_PIN, GPIO_PIN_RESET);
	Set_Speed();
}

void Rover_Right(void)
{
	HAL_GPIO_WritePin(MOTOR_PORT, MOTOR_LEFT_FRONT_PIN, GPIO_PIN_SET);
	HAL_GPIO_WritePin(MOTOR_PORT, MOTOR_RIGHT_FRONT_PIN, GPIO_PIN_RESET);
	HAL_GPIO_WritePin(MOTOR_PORT, MOTOR_LEFT_BACK_PIN, GPIO_PIN_SET);
	HAL_GPIO_WritePin(MOTOR_PORT, MOTOR_RIGHT_BACK_PIN, GPIO_PIN_RESET);
	Set_Speed();
}

void Rover_Left(void)
{
	HAL_GPIO_WritePin(MOTOR_PORT, MOTOR_LEFT_FRONT_PIN, GPIO_PIN_RESET);
	HAL_GPIO_WritePin(MOTOR_PORT, MOTOR_RIGHT_FRONT_PIN, GPIO_PIN_SET);
	HAL_GPIO_WritePin(MOTOR_PORT, MOTOR_LEFT_BACK_PIN, GPIO_PIN_RESET);
	HAL_GPIO_WritePin(MOTOR_PORT, MOTOR_RIGHT_BACK_PIN, GPIO_PIN_SET);
	Set_Speed();
}

void Rover_Stop(void)
{
	adjust_PWM_dutyCycle(MOTOR_PWM_TIMER, TIM_CHANNEL_1, 0);
	adjust_PWM_dutyCycle(MOTOR_PWM_TIMER, TIM_CHANNEL_2, 0);
	adjust_PWM_dutyCycle(MOTOR_PWM_TIMER, TIM_CHANNEL_3, 0);
	adjust_PWM_dutyCycle(MOTOR_PWM_TIMER, TIM_CHANNEL_4, 0);
}


void Rover_Change_Speed(float copySpeed)
{
	if((uint8_t)copySpeed != speed && (uint8_t)copySpeed <= 100 && (uint8_t)copySpeed >= 0){
		lastSpeed = speed;
		speed = copySpeed;
	}
}

static void Set_Speed(void)
{
	if(lastSpeed != speed)
	{
		adjust_PWM_dutyCycle(MOTOR_PWM_TIMER, TIM_CHANNEL_1, speed);
		adjust_PWM_dutyCycle(MOTOR_PWM_TIMER, TIM_CHANNEL_2, speed);
		adjust_PWM_dutyCycle(MOTOR_PWM_TIMER, TIM_CHANNEL_3, speed);
		adjust_PWM_dutyCycle(MOTOR_PWM_TIMER, TIM_CHANNEL_4, speed);
	}
}


static void adjust_PWM_dutyCycle(TIM_HandleTypeDef* pwmHandle, uint32_t pwmChannel, float dutyCycle)
{

    // Calculate the new pulse width based on the duty cycle percentage
    uint32_t maxCCR = pwmHandle->Instance->ARR;
    uint32_t newCCR = (uint32_t)((dutyCycle / 100.0f) * maxCCR);

    // Update the CCR value for the specified channel
    __HAL_TIM_SET_COMPARE(pwmHandle, pwmChannel, newCCR);
}
