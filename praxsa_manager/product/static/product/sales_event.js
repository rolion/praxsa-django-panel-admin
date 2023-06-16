jQuery(function($){
    $(document).ready(function(){
        let items=[];
        let window_films = []

        function get_item_by_id(id){
            return items.find(item => item.part_id == id)
        }
        function get_windows_film_by_id(id){
            return window_films.find(film => film.film_id == id)
        }
        function get_width_element_in_row(brother_selector){
            let parent = $(brother_selector).parents("tr")
            return parent.find('td.field-width input')
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
            return parent.find('td.field-car_part_id select')
        }
        function get_window_film_element_in_row(brother_selector){
            let parent = $(brother_selector).parents("tr")
            return parent.find('td.field-window_film_id select')
        }
        function get_price_element_in_row(brother_selector){
            let parent = $(brother_selector).parents("tr")
            return parent.find('td.field-price input')
        }
        function sum_all_price(){
            let prices = $('table tbody td.field-price input');
            let total_price = 0
            prices.each((index, selector) =>{
                let item = $(selector);
                let value = $.isNumeric(item.val().trim())? parseInt(item.val()):0
                total_price += value
            }, 0)
            $('#id_total_price').val(total_price)
        }
        function add_car_part_event(){
            selects = $('table tbody td.field-car_part_id select').each((index, selector) => {
                let car_model_part_select = $(selector)
                car_model_part_select.change(()=>{
                    // console.log('value selected ', car_model_part_select.val())
                    car_part_item = get_item_by_id(car_model_part_select.val())
                    get_width_element_in_row(car_model_part_select).val(car_part_item.width)
                    get_length_element_in_row(car_model_part_select).val(car_part_item.length)
                    get_quantity_element_in_row(car_model_part_select).val(car_part_item.quantity)
                })
            });
        }
        $('select[name="car_model_id"]').change(function(){
            $.ajax({
                url: '/product/get_car_part_info/'+$(this).val(),
                type:"GET",
                success: function(result) {
                    items = result.items;
                    window_films = result.window_film
                    console.log(result)
                    if (items){
                        console.log(items)
                        add_car_part_event()
                    }
                }
            })
        })
        $('table tbody td.field-window_film_id select').each((index, selector) => {
            select = $(selector).change(function(){
                let selected_film_id = parseInt($(this).val())
                let film = get_windows_film_by_id(selected_film_id)
                let select_part = get_car_part_element_in_row(this)
                let car_part = get_item_by_id(select_part.val())
                total_price = car_part.quantity * parseFloat(film==undefined?0:film.price)
                // input_price = $('#sale_detail_set-'+index+' > td.field-price input').val(total_price)
                get_price_element_in_row(this).val(total_price)
                sum_all_price()
            })
        })
    })
})
