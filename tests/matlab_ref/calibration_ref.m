function cal_vec = calibration_ref(cues, wins, basert, rt_change)
% CALIBRATION_REF  Reference target-window staircase, extracted verbatim from
% the MATLAB MID task (MID-updated/scripts/PresentTarget.m, lines 14-48).
%
% Only the calibration math is kept; the Psychtoolbox Screen/GetKey/timing glue
% is removed and replaced by scripted outcomes so the algorithm can be driven
% deterministically and compared against the Python port (CalibrationState).
%
%   cues      1xN vector of cue ids (1..6), in trial order
%   wins      1xN vector of binary outcomes (1 = hit, 0 = miss/early), trial order
%   basert    base RT in seconds (var.basert)
%   rt_change per-step adjustment in seconds (var.rt_change)
%
% Returns cal_vec: 1xN vector of the target window emitted on each trial
% (data.calibration_vector in the original).

    % Per-cue history, mirroring var.calibrations{1..6} and data.wins{1..6}.
    calibrations = {[],[],[],[],[],[]};
    win_hist     = {[],[],[],[],[],[]};
    cal_vec = zeros(1, numel(cues));

    for ind = 1:numel(cues)
        c = cues(ind);

        % get the calibration vector for this cue
        prior_calibrations = calibrations{c};

        % get the wins vector for this cue
        prior_wins = win_hist{c};

        % if the calibration vector is empty, set calibration to base RT
        if isempty(prior_calibrations)
            current_calibration = basert;

        % if there are at least 3 responses in this category, calculate a
        % recalibration
        elseif length(prior_wins) > 2
            % if the ratio of wins to losses is greater than 0.66, decrement by
            % the specified rt_change. otherwise increment
            ratio = sum(prior_wins)/length(prior_wins);
            if ratio > 0.66
                current_calibration = prior_calibrations(end) - rt_change;
            elseif ratio <= 0.66
                current_calibration = prior_calibrations(end) + rt_change;
            end
        else
            % if under 3 occurences, just set the current calibration to the
            % prior
            current_calibration = prior_calibrations(end);
        end

        % add the current calibration to the prior calibration vector
        prior_calibrations(end+1) = current_calibration;

        % reset the history of calibrations to add the new one
        calibrations{c} = prior_calibrations;

        % add the current calibration to the absolute calibration vector (1D)
        cal_vec(ind) = current_calibration;

        % outcome recorded AFTER the trial (mirrors PresentTarget.m lines 82-115:
        % early press and miss both append 0, a hit appends 1)
        prior_wins(end+1) = wins(ind);
        win_hist{c} = prior_wins;
    end
end
