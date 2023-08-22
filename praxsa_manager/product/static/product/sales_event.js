

jQuery(function($){
    $(document).ready(function(){
        let items=[];
        let window_films = [];
        
        
        function get_car_model_element(){
            return $('select[name="car_model_id"]')
        }

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
            let selects = $('table tbody td.field-car_part_id select');
            selects.each(index => {
                let element = $(selects[index])
                let children = element.children('option');
                children.each(childenIndex => {
                    let option = children[childenIndex];
                    let val = $(option).val()
                    if(!isNaN(val) && !is_part_id_in_model_items(val, items)){
                        $(option).hide()
                    }
                })
            });
        }

        function loadCarInfo(carModelId){
            if(!isNaN(carModelId)){
                $.ajax({
                    url: '/product/get_car_part_info/'+carModelId,
                    type:"GET",
                    success: function(result) {
                        items = result.items;
                        window_films = result.window_film;
                        console.log('items ', items);
                        if (items){
                            add_car_part_event()
                            add_window_film_event()
                            show_only_model_items()
                        }
                    }
                })
            }
        }

        function disable_sale_detail_elements(){
            $('td.field-width input').prop('readonly', true)
            $('td.field-length input').prop('readonly', true)
            $('td.field-quantity input').prop('readonly', true)
            $('td.field-window_film_price input').prop('readonly', true)
            $('td.field-installation_price input').prop('readonly', true)
            $('td.field-sub_total input').prop('readonly', true)
        }

        function onLoad(){
            let selectedModel = get_car_model_element();
            disable_sale_detail_elements()
            if(selectedModel && !isNaN(selectedModel.val())){
                loadCarInfo(selectedModel.val())
            }
        }

        function sum_all_price(){
            let prices = $('table tbody td.field-sub_total input');
            let total_price = 0
            prices.each((index, selector) =>{
                let item = $(selector);
                let value = $.isNumeric(item.val().trim())? parseInt(item.val()):0
                total_price += value
            }, 0)
            $('#id_total_price').val(total_price)
        }

        function clean_film_selection(row){
            get_window_film_element_in_row(row).val('');
            get_price_element_in_row(row).val(0);
            get_installation_price_element_in_row(row).val(0);
            get_sub_total_element_in_row(row).val(0)
            sum_all_price();
        }
        
            
        function add_car_part_event(){
            document.getElementsByTagName('tbody')[3].addEventListener('change', function(e){
                if(e.target && e.target.matches('table tbody td.field-car_part_id select')){
                let car_model_part_select = $(e.target)
                    console.log('value selected ', car_model_part_select.val())
                    car_part_item = get_item_by_id(car_model_part_select.val())
                    get_width_element_in_row(car_model_part_select).val(car_part_item.width)
                    get_width_element_in_row(car_model_part_select).disabled = true
                    get_length_element_in_row(car_model_part_select).val(car_part_item.length)
                    get_quantity_element_in_row(car_model_part_select).val(car_part_item.quantity)
                    clean_film_selection(e.target);
                }
            })

        }
        function add_window_film_event(){
            document.getElementsByTagName('tbody')[3].addEventListener('change', function(e){
                if(e.target && e.target.matches('table tbody td.field-window_film_id select')){
                    let selected_film_id = parseInt($(e.target).val())
                    let select_part = get_car_part_element_in_row(e.target)
                    let itemWidth = get_width_element_in_row(e.target);
                    let filmPrice =getWindowFilmPriceByWidth(itemWidth.val(), selected_film_id);
                    let car_part = get_item_by_id(select_part.val())
                    get_price_element_in_row(e.target).val(filmPrice)
                    get_installation_price_element_in_row(e.target).val(car_part.installation_price)
                    let subtotal = (filmPrice + parseFloat(car_part.installation_price))* car_part.quantity
                    get_sub_total_element_in_row(e.target).val(subtotal)
                    sum_all_price()
                }
            })
        }
        function getWindowFilmPriceByWidth(itemWidth, filmId){
           let price = 0;
           let windowFilmPrice = window_films.filter(item => item.film_id == filmId);
           let prices = windowFilmPrice.filter(film => parseFloat(film.width) === parseFloat(itemWidth))
           if(prices.length == 0 ) {
            let wider_films = window_films.filter(price => parseFloat(price.width) > parseFloat(itemWidth));
            
            prices = wider_films.reduce((acc, curr) =>{
                if(acc != null && acc!=undefined){
                    let discriminate_acc = acc.width - itemWidth;
                    let discriminate_curr = curr.width - itemWidth;
                    if(discriminate_acc >discriminate_curr){
                        return curr;
                    }else{
                        return acc;
                    }
                } else {
                    return curr;
                }
            } )
            price = prices!= undefined && prices != null ? prices.price : 0
           } else {
            price = prices[0].price;
           }
           return parseFloat(price);
        }
        $('select[name="car_model_id"]').change(function(){
            loadCarInfo($(this).val());
        })

        document.addEventListener('formset:added', (event) => {
            if(items.length > 0){
                show_only_model_items()
                // disable_sale_detail_elements();
            }
            
        });
        onLoad();
    })
})
