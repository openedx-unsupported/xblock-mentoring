function MentoringAssessmentView(runtime, element, mentoring) {
    var gradeTemplate = _.template($('#xblock-grade-template').html());
    var reviewQuestionsTemplate = _.template($('#xblock-review-questions-template').html());
    var submitDOM, nextDOM, reviewDOM, tryAgainDOM, messagesDOM, reviewLinkDOM;
    var submitXHR;
    var checkmark;
    var active_child;

    var callIfExists = mentoring.callIfExists;

    function cleanAll() {
        // clean checkmark state
        checkmark.removeClass('checkmark-correct icon-ok fa-check');
        checkmark.removeClass('checkmark-partially-correct icon-ok fa-check');
        checkmark.removeClass('checkmark-incorrect icon-exclamation fa-exclamation');

        /* hide all children */
        $(':nth-child(2)', mentoring.children_dom).remove();

        $('.grade').html('');
        $('.attempts').html('');

        messagesDOM.empty().hide();
    }

    function no_more_attempts() {
        var attempts_data = $('.attempts', element).data();
        return (attempts_data.max_attempts > 0) && (attempts_data.num_attempts >= attempts_data.max_attempts);
    }

    function renderGrade() {
        notify('navigation', {state: 'unlock'})
        var data = $('.grade', element).data();
        data.enable_extended = (no_more_attempts() && data.extended_feedback);
        _.extend(data, {
            'enable_extended': (no_more_attempts() && data.extended_feedback),
            'runDetails': function(label) {
                if (! this.enable_extended) {
                    return '.'
                }
                var self = this;
                return reviewQuestionsTemplate({'questions': self[label], 'label': label})
            }
        });
        cleanAll();
        $('.grade', element).html(gradeTemplate(data));
        reviewDOM.hide();
        reviewLinkDOM.hide();
        submitDOM.hide();
        if (data.enable_extended) {
            nextDOM.unbind('click')
            nextDOM.bind('click', reviewNextChild)
        }
        nextDOM.hide();
        tryAgainDOM.show();

        if (no_more_attempts()) {
            tryAgainDOM.attr("disabled", "disabled");
        }
        else {
            tryAgainDOM.removeAttr("disabled");
        }

        mentoring.renderAttempts();

        if (data.assessment_message && ! no_more_attempts()) {
            mentoring.setContent(messagesDOM, data.assessment_message);
            messagesDOM.show();
        }
        $('a.question-link', element).click(jumpToName);
    }

    function handleTryAgain(result) {
        if (result.result !== 'success')
            return;

        active_child = -1;
        notify('navigation', {state: 'lock'})
        displayNextChild();
        tryAgainDOM.hide();
        submitDOM.show();
        if (! isLastChild()) {
            nextDOM.show();
        }
    }

    function tryAgain() {
        var handlerUrl = runtime.handlerUrl(element, 'try_again');
        if (submitXHR) {
            submitXHR.abort();
        }
        submitXHR = $.post(handlerUrl, JSON.stringify({})).success(handleTryAgain);
    }

    function notify(name, data){
        // Notification interface does not exist in the workbench.
        if (runtime.notify) {
            runtime.notify(name, data)
        }
    }

    function initXBlockView() {
        notify('navigation', {state: 'lock'})
        submitDOM = $(element).find('.submit .input-main');
        nextDOM = $(element).find('.submit .input-next');
        reviewDOM = $(element).find('.submit .input-review');
        reviewLinkDOM = $(element).find('.review-link')
        tryAgainDOM = $(element).find('.submit .input-try-again');
        checkmark = $('.assessment-checkmark', element);
        messagesDOM = $('.assessment-messages', element);

        submitDOM.show();
        submitDOM.bind('click', submit);
        nextDOM.bind('click', displayNextChild);
        nextDOM.show();
        function renderGradeEvent(event) {
            event.preventDefault();
            renderGrade();
        }
        reviewLinkDOM.bind('click', renderGradeEvent)
        reviewDOM.bind('click', renderGradeEvent);
        tryAgainDOM.bind('click', tryAgain);

        active_child = mentoring.step-1;
        mentoring.readChildren();
        displayNextChild();

        mentoring.renderDependency();
    }

    function isLastChild() {
        return (active_child == mentoring.children.length-1);
    }

    function isDone() {
        return (active_child == mentoring.children.length);
    }

    function getByName(name) {
        return $(element).find('div[name="' + name + '"]');
    }

    function jumpToName(event) {
        // Used only during extended feedback. Assumes completion and attempts exhausted.
        event.preventDefault();

        var target = getByName($(event.target).data('name'));
        reviewDisplayChild($.inArray(target[0], mentoring.children_dom), {});
    }

    function reviewDisplayChild(child_index, options) {
        active_child = child_index;
        cleanAll();
        mentoring.displayChild(active_child, options);
        mentoring.publish_event({
            event_type: 'xblock.mentoring.assessment.review',
            exercise_id: $(mentoring.children_dom[active_child]).attr('name')
        });
        post_display(true);
        get_results();
    }

    function reviewNextChild(event) {
        nextDOM.attr('disabled', 'disabled')
        nextDOM.hide()
        findNextChild()
        reviewDisplayChild(active_child)
    }

    function displayNextChild() {
        var options = {
            onChange: onChange
        };

        cleanAll();
        findNextChild(options, true);
        // find the next real child block to display. HTMLBlock are always displayed
        if (isDone()) {
            renderGrade();
        } else {
            post_display();
        }
    }

    function findNextChild(options, fire_event) {
        // Finds the next child, and does initial display. Intended to be called by a proper display
        // wrapper like displayNextChild or reviewNextChild.
        options = options || {};
        ++active_child;
        while (1) {
            var child = mentoring.displayChild(active_child, options);
            if (fire_event) {
                mentoring.publish_event({
                    event_type: 'xblock.mentoring.assessment.shown',
                    exercise_id: $(child).attr('name')
                });
            }
            if ((typeof child !== 'undefined') || active_child >= mentoring.children.length-1)
                break;
            ++active_child;
        }
    }

    function post_display(show_link) {
        nextDOM.attr('disabled', 'disabled');
        if (no_more_attempts()) {
            if (show_link) {
                reviewLinkDOM.show();
            } else {
                reviewDOM.show();
                reviewDOM.removeAttr('disabled')
            }
        } else {
            reviewDOM.attr('disabled', 'disabled');
        }
        validateXBlock(show_link);
        if (show_link && ! isLastChild()) {
            // User should also be able to browse forward if we're showing the review link.
            nextDOM.show();
            nextDOM.removeAttr('disabled');
        }
        if (show_link) {
            // The user has no more tries, so the try again button is noise. A disabled submit button
            // emphasizes that the user cannot change their answer.
            tryAgainDOM.hide();
            submitDOM.show()
            submitDOM.attr('disabled', 'disabled')
        }
    }

    function onChange() {
        // Assessment mode does not allow to modify answers.
        // Once an answer has been submitted (next button is enabled),
        // start ignoring changes to the answer.
        if (nextDOM.attr('disabled')) {
            validateXBlock();
        }
    }

    function handleResults(response) {
        $('.grade', element).data('score', response.score);
        $('.grade', element).data('correct_answer', response.correct_answer);
        $('.grade', element).data('incorrect_answer', response.incorrect_answer);
        $('.grade', element).data('partially_correct_answer', response.partially_correct_answer);
        $('.grade', element).data('max_attempts', response.max_attempts);
        $('.grade', element).data('num_attempts', response.num_attempts);
        $('.grade', element).data('assessment_message', response.assessment_message);
        $('.attempts', element).data('max_attempts', response.max_attempts);
        $('.attempts', element).data('num_attempts', response.num_attempts);

        if (response.completed === 'partial') {
            checkmark.addClass('checkmark-partially-correct icon-ok fa-check');
        } else if (response.completed === 'correct') {
            checkmark.addClass('checkmark-correct icon-ok fa-check');
        } else {
            checkmark.addClass('checkmark-incorrect icon-exclamation fa-exclamation');
        }

        submitDOM.attr('disabled', 'disabled');

        /* We're not dealing with the current step */
        if (response.step != active_child+1) {
            return
        }
        nextDOM.removeAttr("disabled");
        reviewDOM.removeAttr("disabled");
    }

    function handleReviewResults(response) {
        handleResults(response);
        var options = {
            max_attempts: response.max_attempts,
            num_attempts: response.num_attempts
        };
        var result = response.results[1];
        var child = mentoring.children[active_child];
        callIfExists(child, 'handleSubmit', result, options);
        callIfExists(child, 'handleReview', result, options);
    }

    function handleSubmitResults(response){
        handleResults(response);
        // Update grade information
        $('.grade').data(response);
    }

    function calculate_results(handler_name, successs_callback, error_callback) {
        if (typeof error_callback === 'undefined'){
            error_callback = function () {};
        }
        var data = {};
        var child = mentoring.children[active_child];
        if (child && child.name !== undefined) {
            data[child.name] = callIfExists(child, handler_name);
        }
        var handlerUrl = runtime.handlerUrl(element, handler_name);
        if (submitXHR) {
            submitXHR.abort();
        }
        var opts = {
            type: "POST",
            url: handlerUrl,
            data: JSON.stringify(data),
            contentType: 'application/json',
            success: successs_callback,
            error: error_callback
        };
        submitXHR = $.ajax(opts)
    }

    function submit() {
        submitDOM.attr('disabled', 'disabled');
        errorCallback = function () {
            submitDOM.removeAttr("disabled");
        };
        calculate_results('submit', handleSubmitResults, errorCallback);
    }

    function get_results() {
        calculate_results('get_results', handleReviewResults)
    }

    function validateXBlock(hide_nav) {
        var is_valid = true;

        var child = mentoring.children[active_child];
        if (child && child.name !== undefined) {
            var child_validation = callIfExists(child, 'validate');
            if (_.isBoolean(child_validation)) {
                is_valid = is_valid && child_validation;
            }
        }


        if (!is_valid) {
            submitDOM.attr('disabled','disabled');
        }
        else {
            submitDOM.removeAttr("disabled");
        }

        if (isLastChild() && ! hide_nav) {
            nextDOM.hide();
            reviewDOM.show();
        }

    }

    initXBlockView();

}
