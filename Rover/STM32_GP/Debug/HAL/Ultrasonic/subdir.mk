################################################################################
# Automatically-generated file. Do not edit!
# Toolchain: GNU Tools for STM32 (11.3.rel1)
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
../HAL/Ultrasonic/ultrasonic.c 

OBJS += \
./HAL/Ultrasonic/ultrasonic.o 

C_DEPS += \
./HAL/Ultrasonic/ultrasonic.d 


# Each subdirectory must supply rules for building sources it contributes
HAL/Ultrasonic/%.o HAL/Ultrasonic/%.su HAL/Ultrasonic/%.cyclo: ../HAL/Ultrasonic/%.c HAL/Ultrasonic/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -g3 -DDEBUG -DUSE_HAL_DRIVER -DSTM32F401xC -c -I../Core/Inc -I../Drivers/STM32F4xx_HAL_Driver/Inc -I../Drivers/STM32F4xx_HAL_Driver/Inc/Legacy -I../Drivers/CMSIS/Device/ST/STM32F4xx/Include -I../Drivers/CMSIS/Include -I"C:/Users/Ehab/Documents/ARM/STM32_GP/HAL" -I"C:/Users/Ehab/Documents/ARM/STM32_GP/HAL/Ultrasonic" -I"C:/Users/Ehab/Documents/ARM/STM32_GP/HAL/Motor" -O0 -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfpu=fpv4-sp-d16 -mfloat-abi=hard -mthumb -o "$@"

clean: clean-HAL-2f-Ultrasonic

clean-HAL-2f-Ultrasonic:
	-$(RM) ./HAL/Ultrasonic/ultrasonic.cyclo ./HAL/Ultrasonic/ultrasonic.d ./HAL/Ultrasonic/ultrasonic.o ./HAL/Ultrasonic/ultrasonic.su

.PHONY: clean-HAL-2f-Ultrasonic

