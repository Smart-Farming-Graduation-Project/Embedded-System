/*
 * ultrasonic.h
 *
 *  Created on: Feb 21, 2025
 *      Author: Ehab
 */

#ifndef ULTRASONIC_ULTRASONIC_H_
#define ULTRASONIC_ULTRASONIC_H_

#include "stm32f4xx_hal.h"

#define ULTRASONUC_TRIGGER_PORT			GPIOB
#define ULTRASONIC_TRIGGER_PIN  		GPIO_PIN_2
#define ULTRASONIC_ECHO_PIN_IC  		&htim2          // GPIO_PIN_10 (CH3)

void Ultrasnoic_Initialize(void);
void Ultrasonic_Get_Distance(void);

#endif /* ULTRASONIC_ULTRASONIC_H_ */
