# l10n_co_edi_jorels_pos

Modulo POS de facturación electrónica libre por Jorels SAS
----------------------------------------------------------

Con este módulo puedes facturar electrónicamente con la DIAN desde el POS. Adicionalmente puedes elegir entre usar el 
recibo de siempre, la factura normal no electrónica o bien si el cliente lo desea emitir la factura electrónica 
correspondiente. 

Esto se consigue, pues es posible elegir un diario diferente para la facturación normal y otro para la factura 
electrónica; logrando así una independencia entre las secuencias.

El correo electrónico es enviado automáticamente al cliente, habilitando esta opción en la configuración y solo será 
enviado si la factura ha sido validada ante la DIAN en entorno de producción.

El ticket de venta se ha personalizado para asemejarse a una factura electrónica, incluyendo los parámetros de ley como 
el CUFE, CUDE, resolución de facturación, nombre del cliente, documento, Nit de la empresa, etc.

Se ha personalizado la interfaz de clientes para poder ingresar desde el POS todos los detalles del cliente exigidos por
la DIAN, como tipo de responsabilidad, tipo de regimen, correo de facturación electrónica, municipalidad, etc.

Este módulo es totalmente compatible con el módulo de facturación electrónica de Jorels y al igual que este último, se 
encuentra liberado bajo licencia LGPL.

Este modulo aún está en pruebas en la versión 14 y no debe ser usado en producción
