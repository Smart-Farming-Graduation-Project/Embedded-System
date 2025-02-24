################################################################################
# Automatically-generated file. Do not edit!
# Toolchain: GNU Tools for STM32 (11.3.rel1)
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
../HAL/Motor/motor.c 

OBJS += \
./HAL/Motor/motor.o 

C_DEPS += \
./HAL/Motor/motor.d 


# Each subdirectory must supply rules for building sources it contributes
HAL/Motor/%.o HAL/Motor/%.su HAL/Motor/%.cyclo: ../HAL/Motor/%.c HAL/Motor/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -g3 -DDEBUG -DUSE_HAL_DRIVER -DSTM32F401xC -c -I../Core/Inc -I../Drivers/STM32F4xx_HAL_Driver/Inc -I../Drivers/STM32F4xx_HAL_Driver/Inc/Legacy -I../Drivers/CMSIS/Device/ST/STM32F4xx/Include -I../Drivers/CMSIS/Include -I"C:/Users/Ehab/Documents/ARM/STM32_GP/HAL" -I"C:/Users/Ehab/Documents/ARM/STM32_GP/HAL/Ultrasonic" -I"C:/Users/Ehab/Documents/ARM/STM32_GP/HAL/Motor" -O0 -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfpu=fpv4-sp-d16 -mfloat-abi=hard -mthumb -o "$@"

clean: clean-HAL-2f-Motor

clean-HAL-2f-Motor:
	-$(RM) ./HAL/Motor/motor.cyclo ./HAL/Motor/motor.d ./HAL/Motor/motor.o ./HAL/Motor/motor.su

.PHONY: clean-HAL-2f-Motor

