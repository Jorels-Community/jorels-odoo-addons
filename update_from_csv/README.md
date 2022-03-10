Update from CSV
===============

Update from csv, insert values, using function; without external_id's. For example:

    <?xml version="1.0" encoding="utf-8"?>
    <odoo>
        <data noupdate="1">
            <function
                    model="res.company"
                    name="init_csv_data"
                    eval="[0,'module_name.fleet.vehicle.model.brand']"
            />
            <function
                    model="res.company"
                    name="init_csv_data"
                    eval="[0,'module_name.fleet.vehicle.model']"
            />
        </data>
    </odoo>

The data might be .../module_name/data/module_name.fleet.vehicle.model.brand.csv

Example csv data:

For fleet.vehicle.model.brand.csv:

    "id","name"
    1,"CHEVROLET"
    2,"DAEWOO"
    3,"FIAT"
    .
    .
    .

For fleet.vehicle.model.csv:

    "id","brand_id","name"
    1,"1","TAXI 7:24"
    2,"1","454 SS"
    3,"1","ALTO"
    .
    .
    .


![Jorels](https://www.jorels.com/web/image/res.company/1/logo)
Under LGPL v3 License by Jorels SAS
