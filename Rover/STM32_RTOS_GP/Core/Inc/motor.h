/*****************************************************************************************
 ****************** @file           : dcmotor.h		         	      ********************
 ****************** @author         : Ehab Magdy Abdallah             ********************
 ****************** @brief          : interface file DC Motor         ********************
******************************************************************************************/

#ifndef DCMOTOR_DCMOTOR_H_
#define DCMOTOR_DCMOTOR_H_

/******************************          Includes           ******************************/
#include "stm32f4xx_hal.h"
extern TIM_HandleTypeDef htim3;		// pwm

/******************************   MACRO Decelerations       ******************************/
#define MOTOR_PORT					GPIOA

#define MOTOR_LEFT_FRONT_PIN	    GPIO_PIN_0
#define MOTOR_RIGHT_FRONT_PIN	    GPIO_PIN_1
#define MOTOR_LEFT_BACK_PIN	        GPIO_PIN_2
#define MOTOR_RIGHT_BACK_PIN	    GPIO_PIN_3

#define MOTOR_PWM_TIMER			  	&htim3
// PWM pins: A6,A7,B0,B1

/******************************      Software intefaces      ******************************/
void Rover_Initialize(void);
void Rover_Forward(void);
void Rover_Backward(void);
void Rover_Right(void);
void Rover_Left(void);
void Rover_Stop(void);
void Rover_Change_Speed(float speed);

#endif /* DCMOTOR_DCMOTOR_H_ */
