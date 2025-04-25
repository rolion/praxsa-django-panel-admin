jQuery(function($){
    $(document).ready(function(){
        let items=[];
        let window_films = [];
        let inventario = [];
        let widths = []
        
        function get_car_model_element(){
            return $('select[name="car_model_id"]')
        }

        function get_item_by_id(id){
            return items.find(item => item.part_id == id)
        }

        function get_sale_type_element(){
            return $('select[name="sales_type"]')
        }

        function get_sucursal_id(){
            console.log('call get sucursal element')
            let user_sucursal = $('select[name="sucursal"]')
            if (!isNaN(user_sucursal.val())){
                return user_sucursal.val()
            }
            url = $("#proforma_header_form > div > fieldset:nth-child(1) > div.form-row.field-sucursal > div > div > div > a").attr("href")
            sucursal_id= url.replace(/[\D+]/g, '')
            return sucursal_id
        }
        function get_width_element_in_row(brother_selector){
            let parent = $(brother_selector).parents("tr")
            return parent.find('td.field-width select')
        }

        function get_wdisponibilidad_element_in_row(brother_selector){
            let parent = $(brother_selector).parents("tr")
            return parent.find('td.field-disponibilidad input')
        }
        function get_length_element_in_row(brother_selector){
            let parent = $(brother_selector).parents("tr")
            return parent.find('td.field-length input')
        }
        function get_quantity_element_in_row(brother_selector){
            let parent = $(brother_selector).parents("tr")
            return parent.find('td.field-quantity input')
        }
        function get_car_part_element_in_row(brother_selector){
            let parent = $(brother_selector).parents("tr")
            return parent.find('td.field-car_part select')
        }
        function get_window_film_element_in_row(brother_selector){
            let parent = $(brother_selector).parents("tr")
            return parent.find('td.field-window_film select')
        }
        function get_price_element_in_row(brother_selector){
            let parent = $(brother_selector).parents("tr")
            return parent.find('td.field-window_film_price input')
        }
        function get_installation_price_element_in_row(brother_selector){
            let parent = $(brother_selector).parents("tr")
            return parent.find('td.field-installation_price input')
        }
        function get_sub_total_element_in_row(brother_selector){
            let parent = $(brother_selector).parents("tr")
            return parent.find('td.field-sub_total input')
        }

        function find_part_id_in_model_items(part_id, items){
            if(items.length == 0){
                return undefined;
            }
            return items.find(item => item.part_id == part_id)
        }

        function is_part_id_in_model_items(part_id, items){
            if(items.length == 0){
                return false;
            }
            return find_part_id_in_model_items(part_id, items) == undefined? false: true;
        }

        function show_only_model_items(){
            let selects = $('table tbody td.field-car_part select');
            selects.each(index => {
                let element = $(selects[index])
                let children = element.children('option');
                children.each(childenIndex => {
                    let option = children[childenIndex];
                    let val = $(option).val()
                    if(!isNaN(val) && !is_part_id_in_model_items(val, items)){
                        $(option).hide()
                    }
                    else{
                        $(option).show();
                    }
                })
            });
        }

        function loadCarInfo(carModelId, sucursalId){
            if(!isNaN(carModelId)){
                $.ajax({
                    url: '/product/get_car_part_info/'+carModelId+'/'+sucursalId,
                    type:"GET",
                    success: function(result) {
                        items = result.items;
                        window_films = result.window_film;
                        widths = result.inv_widths
                        console.log('items ', items);
                        console.log('window films', window_films)
                        console.log('widths', widths)
                        if (items){
                            add_car_part_event()
                            add_window_film_event()
                            show_only_model_items()
                            if (is_sale_instalation_type() == false && items.length > 0){
                                let model_name = get_car_model_element().children("option").filter(":selected").text()
                                let rows = '';
                                resume = items.reduce((acc, curr)=>{
                                    if (`${curr.width}` in acc){
                                        acc[`${curr.width}`] = parseFloat(acc[`${curr.width}`]) + (parseFloat(curr.length) * curr.quantity)
                                    }else{
                                        acc[`${curr.width}`] = parseFloat(curr.length) * curr.quantity
                                    }
                                    return acc
                                }, {})
                                console.log('itmes', items)
                                $.each(resume, function(key, value){
                                    rows+= `
                                            <tr class="form-row has_original dynamic-items" id="">
                                                
                                                <td class="field-width">
                                                    <p>${key}</p>
                                                </td>
                                                <td class="field-length">
                                                    <p>${value.toFixed(2)}</p>
                                                </td>
                                            </tr>
                                    `
                                })
                                let container = `
                                <br>
                                <div id="model-item-helper" class="tabular inline-related last-related">
                                    <fieldset class="module ">
                                        <h2> ${model_name}</h2>
                                        <table>
                                            <thead>
                                                <tr>
                                                    <th class="column-width">Ancho</th>
                                                    <th class="column-length">Largo</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                            ${rows}
                                            </tbody>
                                        </table>
                                    </fieldset>
                                </div>`
                                $('#model-item-helper').remove()
                                $('#items-group').append(container)
                        }
                        }
                    }
                })
            }
        }

        function loadInventory(sucursalId){
            if(!isNaN(sucursalId)){
                $.ajax({
                    url: '/product/get_inventory/'+sucursalId+'/0/0',
                    type:"GET",
                    success: function(result) {
                        inventario = result.inventario;
                        console.log('inventory ->', inventario)
                    }
                })
            }
        }
        function is_sale_instalation_type(){
            return get_sale_type_element().val() === 'venta_instalacion'
        }
        function disable_sale_detail_elements(){
            $('td.field-width input').prop('readonly', true)
            // $('td.field-quantity input').prop('readonly', true)
            $('td.field-window_film_price input').prop('readonly', true)
            // $('td.field-installation_price input').prop('readonly', true)
            $('td.field-sub_total input').prop('readonly', true)
            $('td.field-car_part > select').prop('disabled', false)
            if(is_sale_instalation_type()){
                $('td.field-length input').prop('readonly', true)
            }else {
                $('td.field-length input').prop('readonly', false)
                // $('td.field-car_part select').prop('disabled', true)
            }
        }

        function onLoad(){
            console.log('onload called')
            let selectedModel = get_car_model_element();
            let user_sucursal = get_sucursal_id();
            disable_sale_detail_elements();
            console.log('selected model ', selectedModel.val(), 'is NaN ', isNaN(selectedModel.val()))
            $('input[name="total_price"]').prop('readonly', true)
            if(selectedModel && user_sucursal && !isNaN(user_sucursal)){
                model_id = isNaN(selectedModel.val()) || selectedModel.val()==''? 0 : selectedModel.val()
                loadCarInfo(model_id, user_sucursal)
                loadInventory(user_sucursal)
                //show_only_model_items()

            }
        }

        function sum_all_price(){
            let prices = $('table > tbody > tr > td.field-sub_total > input');
            let total_price = 0
            prices.each((index, selector) =>{
                let item = $(selector);
                let value = $.isNumeric(item.val().trim())? parseFloat(item.val()):0
                total_price += value
            }, 0)
            console.log(`total price ${total_price.toFixed(2)}`)
            $('#id_total_price').val(total_price.toFixed(2))
        }

        function clean_film_selection(row){
            get_window_film_element_in_row(row).val('');
            get_price_element_in_row(row).val(0);
            get_installation_price_element_in_row(row).val(0);
            get_sub_total_element_in_row(row).val(0)
            sum_all_price();
        }
        getNextWidth = (originalW) => {
            biggerWidths = widths.filter(w => parseFloat(w) > parseFloat(originalW))
            if(biggerWidths.length > 0){
                return biggerWidths[0]
            }
            return undefined
        }
        
        function get_ancho(item){
            let is_item_width_in_array = widths.find(w => parseFloat(w) == parseFloat(item.width))
            if(is_item_width_in_array != undefined){
                return item.width
            }
            return getNextWidth(item.width)

        }
        can_update_sub_total_venta_instalacion = (target) =>{
            lamina = get_window_film_element_in_row(target).val()
            item = get_car_part_element_in_row(target).val()
            if (item && lamina){
                return true
            }
            return false;
        }
        can_update_sub_total_metro_lamina = (target) =>{
            lamina = get_window_film_element_in_row(target).val()
            length = get_length_element_in_row(target).val()
            if (lamina && length){
                return true
            }
            return false;
        }
        calculate_subtotal = (target) => {
            let sales_type = get_sale_type_element().val()
            if(sales_type == 'venta_instalacion'){
                if(can_update_sub_total_venta_instalacion(target)){
                    let film_price = parseFloat(get_price_element_in_row(target).val())
                    let installation_price = parseFloat(get_installation_price_element_in_row(target).val())
                    let quantity = parseInt(get_quantity_element_in_row(target).val())
                    let length = parseFloat(get_length_element_in_row(target).val())
                    let subtotal = ((length * quantity) * film_price) + (installation_price * quantity)
                    get_sub_total_element_in_row(target).val(subtotal.toFixed(2))
                    sum_all_price()
                }
                
            }else{
                if(can_update_sub_total_metro_lamina(target)){
                    let film_price = parseFloat(parseFloat(get_price_element_in_row(target).val()))
                    let length = parseFloat(get_length_element_in_row(target).val())
                    let subtotal = length * film_price
                    get_sub_total_element_in_row(target).val(subtotal.toFixed(2))
                    sum_all_price()
                }
            }
         }

        function onChangeTableRow(e){
            if(e.target && e.target.matches('table tbody td.field-car_part select')){
                let car_model_part_select = $(e.target)
                console.log('value selected ', car_model_part_select.val())
                car_part_item = get_item_by_id(car_model_part_select.val())
                console.log('item selected ', car_part_item)
                get_width_element_in_row(car_model_part_select).val(get_ancho(car_part_item))
                get_length_element_in_row(car_model_part_select).val(car_part_item.length)
                get_quantity_element_in_row(car_model_part_select).val(car_part_item.quantity)
                get_installation_price_element_in_row(e.target).val(car_part_item.installation_price)
                calculate_subtotal(e.target)
            }
        }
        function add_car_part_event(){
            document.querySelector("#items-group > div > fieldset > table").removeEventListener('change', onChangeTableRow)
            document.querySelector("#items-group > div > fieldset > table").addEventListener('change', onChangeTableRow)

         }

         filterFilmById = (filmId) => window_films.filter(film => film.film_id == filmId)
         getFilmByIdWidth = (filmId, width) => window_films.find(film => film.film_id == filmId && film.width == width)
         getItemById = (itemID)=> items.find(item => item.part_id == itemID)
         filterItemById = (id) => items.filter(item => item.part_id == id)
         


        get_disponibilidad_lamina = (film_id, film_width) =>{
            let dispo = inventario.find(inv => inv.bobina_film_id == film_id && inv.bobina_width == film_width)
            if(dispo){
                return dispo.bobina_metros_disponibles
            }
            film = window_films.find(film => film.film_id == film_id)
            alert(`no se encontro la lamina ${film.name} en el inventario con ancho ${film_width}, utilice otra lamina o modifique el ancho`);
            console.log(`no se encontro la lamina en el inventario, id = ${film_id} width = ${film_width}`)
            return 0;
        }
        update_diponibilidad_value = (dispo, target) => {
            get_wdisponibilidad_element_in_row(target).val(dispo)
        }

        updateFilmPrice = (filmId, width, target) => {
            let selected_film = getFilmByIdWidth(filmId, width);
            if(selected_film !=undefined){
                get_price_element_in_row(target).val(selected_film.price)
            }
            let dispo = get_disponibilidad_lamina(filmId, width)
            update_diponibilidad_value(dispo, target)
         }
        
        function onLaminaChangeEvent(e){
            if(e.target && e.target.matches('table tbody td.field-window_film select')){
                console.log('cambio la lamina');
                // let sale_type = get_sale_type_element();
                let selected_film_id = parseInt($(e.target).val())
                
                let selected_width = get_width_element_in_row(e.target).val();
                let selected_lenght = get_length_element_in_row(e.target).val();
                updateFilmPrice(selected_film_id, selected_width, e.target)
                calculate_subtotal(e.target)
            }
            if(e.target && e.target.matches('table tbody td.field-width select')){
                console.log('cambio el ancho');
                let selected_width = parseFloat($(e.target).val())
                let selected_film_id =get_window_film_element_in_row(e.target).val();
                if(selected_film_id){
                    console.log('se eligio una lamina')
                    updateFilmPrice(selected_film_id, selected_width, e.target)
                    calculate_subtotal(e.target)
                }
            }
            if(e.target && e.target.matches('table tbody td.field-length input')){
                calculate_subtotal(e.target)
            }
        }
        
        function add_window_film_event(){
            document.querySelector("#items-group > div > fieldset > table").removeEventListener('change', onLaminaChangeEvent)
            document.querySelector("#items-group > div > fieldset > table").addEventListener('change', onLaminaChangeEvent)
        }

        $('select[name="car_model_id"], select[name="sales_type"]').change(function(e){
            onLoad()
            
        })

        
        $('select[name="car_model_id"]').change(function(e){
            delete_buttons = $('td.delete > div > a')
            if (delete_buttons.length > 0){
                delete_buttons.each(function(index, button){

                    button.click()
                })
            }
        })
        

        document.addEventListener('formset:added', (event) => {
            if(items.length > 0){
                show_only_model_items()
                disable_sale_detail_elements();
            }
            
        });
        document.addEventListener('formset:removed', (event) => {
            if(items.length > 0){
                sum_all_price()
            }
            
        });
        onLoad();
    })
})